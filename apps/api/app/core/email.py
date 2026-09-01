"""Outbound email.

One function, two providers, chosen by `EMAIL_PROVIDER`. Callers compose the
message; nothing here knows what a magic link is.

`console` logs the message instead of sending it. It exists so development
needs no mail account, and it is refused in production by
`check_production_hardening` — a logged magic link is a working sign-in for
anyone who can read the log.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class EmailDeliveryError(RuntimeError):
    """The provider refused the message. The caller decides whether that is
    fatal — for sign-in it must be, or the user waits for a mail that will
    never arrive."""


async def send_email(*, to: str, subject: str, text: str, html: str) -> None:
    if settings.email_provider == "console":
        # Never at INFO in a deployed environment: this line contains the
        # body, and for sign-in the body contains a live token.
        log.info("email.console", to=to, subject=subject, body=text)
        return

    if settings.email_provider == "resend":
        await _send_resend(to=to, subject=subject, text=text, html=html)
        return

    raise EmailDeliveryError(f"EMAIL_PROVIDER '{settings.email_provider}' is not configured")


async def _send_resend(*, to: str, subject: str, text: str, html: str) -> None:
    if not settings.resend_api_key:
        raise EmailDeliveryError("RESEND_API_KEY is not set")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                RESEND_ENDPOINT,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.email_from,
                    "to": [to],
                    "subject": subject,
                    "text": text,
                    "html": html,
                },
            )
    except httpx.HTTPError as exc:
        raise EmailDeliveryError(f"resend unreachable: {type(exc).__name__}") from exc

    if response.status_code >= 400:
        # The provider's body can echo the recipient; log the status only.
        log.warning("email.resend.rejected", status=response.status_code)
        raise EmailDeliveryError(f"resend returned {response.status_code}")

    log.info("email.sent", provider="resend", status=response.status_code)
