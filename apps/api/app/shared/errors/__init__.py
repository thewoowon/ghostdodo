"""Error envelope shared by every endpoint (specs/API_CONTRACT.md).

    {"error": {"code", "message", "request_id", "details"}}

`message` is user-facing Korean. `code` is the stable machine identifier the
web client switches on — never localize or rename a code.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for expected, mapped failures."""

    status_code: int = 400
    code: str = "BAD_REQUEST"
    message: str = "요청을 처리할 수 없습니다."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "찾을 수 없습니다."


class CompanyNotFoundError(NotFoundError):
    code = "COMPANY_NOT_FOUND"
    message = "해당 회사를 찾을 수 없습니다."


class ReportNotFoundError(NotFoundError):
    code = "REPORT_NOT_FOUND"
    message = "해당 기록을 찾을 수 없습니다."


class JobNotFoundError(NotFoundError):
    code = "JOB_NOT_FOUND"
    message = "해당 공고를 찾을 수 없습니다."


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "로그인이 필요합니다."


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "권한이 없습니다."


class AuthProviderError(AppError):
    """Any failure inside an external sign-in flow.

    One message for every cause — a bad state, a replayed code, a token for
    another client — so a probe cannot map the flow's internals.
    """

    status_code = 401
    code = "AUTH_PROVIDER_FAILED"
    message = "로그인을 완료하지 못했습니다. 다시 시도해 주세요."


class AuthProviderUnavailableError(AppError):
    status_code = 503
    code = "AUTH_PROVIDER_UNAVAILABLE"
    message = "구글 로그인이 아직 설정되지 않았습니다."


class EmailDeliveryFailedError(AppError):
    """The magic link could not be handed to the mail provider.

    Reported as a failure rather than swallowed: a 202 here would tell the
    user to go check an inbox that will never receive anything. It carries
    no information about whether the address has an account.
    """

    status_code = 502
    code = "EMAIL_DELIVERY_FAILED"
    message = "로그인 링크를 보내지 못했습니다. 잠시 후 다시 시도해 주세요."


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "입력값을 확인해 주세요."


class ReportNotEditableError(AppError):
    status_code = 409
    code = "REPORT_NOT_EDITABLE"
    message = "검토가 시작된 기록은 직접 수정할 수 없습니다."


class DuplicateReportError(AppError):
    status_code = 409
    code = "DUPLICATE_REPORT"
    message = "동일한 채용 과정에 대한 기록이 이미 있습니다."


class ReportLimitError(AppError):
    status_code = 429
    code = "REPORT_LIMIT_REACHED"
    message = "같은 회사에 대해 등록할 수 있는 기록 수를 초과했습니다."


class EvidenceTooLargeError(AppError):
    status_code = 413
    code = "EVIDENCE_TOO_LARGE"
    message = "첨부 파일이 너무 큽니다."


class UnsupportedEvidenceTypeError(AppError):
    status_code = 415
    code = "UNSUPPORTED_EVIDENCE_TYPE"
    message = "지원하지 않는 파일 형식입니다."


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    message = "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요."


class FeatureDisabledError(AppError):
    status_code = 404
    code = "FEATURE_DISABLED"
    message = "아직 공개되지 않은 기능입니다."


class ProhibitedContentError(AppError):
    status_code = 422
    code = "PROHIBITED_CONTENT"
    message = "개인 신상 정보나 단정적 비방 표현은 기록할 수 없습니다."
