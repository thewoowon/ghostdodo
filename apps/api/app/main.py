"""GhostDodo API entrypoint."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import orjson
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import configure_logging, get_logger, request_id_var
from app.core.methodology import CURRENT_METHODOLOGY_VERSION, get_methodology
from app.core.redis import close_redis, get_redis
from app.db.session import db_session, dispose_engine
from app.modules.auth.router import router as auth_router
from app.modules.companies.router import router as companies_router
from app.modules.disputes.router import router as disputes_router
from app.modules.jobs.router import router as jobs_router
from app.modules.moderation.router import router as admin_router
from app.modules.reports.router import router as reports_router
from app.modules.users.router import router as me_router
from app.shared.errors import AppError

log = get_logger(__name__)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level, json_output=settings.app_env != "development")
    settings.check_production_hardening()
    log.info("api.startup", env=settings.app_env, methodology=CURRENT_METHODOLOGY_VERSION)
    yield
    await close_redis()
    await dispose_engine()
    log.info("api.shutdown")


app = FastAPI(
    title="GhostDodo API",
    version="0.1.0",
    description="지원자가 남긴 채용 응답 기록 데이터베이스",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)

# Strict CORS: only the known web origin, credentials allowed for session cookie.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Idempotency-Key", "X-CSRF-Token"],
    max_age=600,
)


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Assigns a request id, binds it to logs, and echoes it back so a user
    report can be traced to exactly one server-side request."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    token = request_id_var.set(request_id)
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        # Logged before the contextvar is reset, so the access line actually
        # carries the id rather than the "-" placeholder.
        log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(elapsed_ms, 2),
        )
        return response
    finally:
        request_id_var.reset(token)


@app.middleware("http")
async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    # API responses are per-user; never let a shared cache hold one.
    response.headers.setdefault("Cache-Control", "no-store")
    return response


_HTTP_ERROR_CODES: dict[int, str] = {
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    429: "RATE_LIMITED",
}

_HTTP_ERROR_MESSAGES: dict[int, str] = {
    401: "로그인이 필요합니다.",
    403: "권한이 없습니다.",
    404: "찾을 수 없습니다.",
    405: "허용되지 않은 요청 방식입니다.",
    429: "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.",
}


def _error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "details": details or {},
            }
        },
    )


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return _error_response(
        exc.status_code,
        exc.code,
        exc.message,
        getattr(request.state, "request_id", "-"),
        exc.details,
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        422,
        "VALIDATION_ERROR",
        "입력값을 확인해 주세요.",
        getattr(request.state, "request_id", "-"),
        {"fields": orjson.loads(orjson.dumps(exc.errors(), default=str))},
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Normalizes framework-raised errors (404 from the router, 405, ...) into
    the same envelope as domain errors, so the client has one shape to parse."""
    code = _HTTP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR")
    message = _HTTP_ERROR_MESSAGES.get(exc.status_code, "요청을 처리할 수 없습니다.")
    response = _error_response(
        exc.status_code, code, message, getattr(request.state, "request_id", "-")
    )
    if exc.headers:
        response.headers.update(exc.headers)
    return response


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    log.exception("http.unhandled", path=request.url.path, error=str(exc))
    # Never leak internals to the client; the request id links to the log line.
    return _error_response(500, "INTERNAL_ERROR", "일시적인 오류가 발생했습니다.", request_id)


@app.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def health_ready() -> JSONResponse:
    """Readiness includes dependencies — a pod that cannot reach Postgres or
    Redis must not receive traffic."""
    checks: dict[str, str] = {}
    try:
        async with db_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
    try:
        await get_redis().ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {type(exc).__name__}"

    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "degraded", "checks": checks},
    )


# ── Routes ────────────────────────────────────────────────────────────────
# Every business route lives under /api/v1; health checks stay unversioned
# so an orchestrator's probe never breaks on an API version bump.
for _router in (
    auth_router,
    companies_router,
    reports_router,
    me_router,
    admin_router,
    disputes_router,
    jobs_router,
):
    app.include_router(_router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/methodology", tags=["methodology"])
async def methodology_summary() -> dict[str, object]:
    """The public methodology, served from the same source the calculations
    read — the page and the numbers cannot drift apart."""
    m = get_methodology()
    return {
        "version": m.version,
        "stage_thresholds": {
            stage.value: {
                "silence_days": t.silence_days,
                "analytic_weight": t.analytic_weight,
            }
            for stage, t in m.stage_thresholds.items()
        },
        "promise_grace_days": m.promise_grace_days,
        "eligibility": {
            state.value: {
                "min_qualified_n": bar.min_qualified_n,
                "min_verified_ratio": bar.min_verified_ratio,
            }
            for state, bar in m.eligibility.items()
        },
        "recency_windows": list(m.recency_windows),
        "default_public_window": m.default_public_window,
    }
