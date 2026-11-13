"""Fixed-window rate limiting backed by Redis.

Deliberately simple: the goal is throttling abuse bursts, not precise
metering. Limits are declared next to the route they protect.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.core.redis import get_redis
from app.shared.errors import RateLimitedError


@dataclass(frozen=True, slots=True)
class RateLimit:
    limit: int
    window_seconds: int

    @property
    def key_suffix(self) -> str:
        return f"{self.limit}/{self.window_seconds}"


# Named limits, so the policy is visible in one place.
SIGN_IN_REQUEST = RateLimit(limit=5, window_seconds=15 * 60)
REPORT_SUBMIT = RateLimit(limit=10, window_seconds=24 * 60 * 60)
EVIDENCE_UPLOAD = RateLimit(limit=30, window_seconds=60 * 60)
COMMUNITY_POST = RateLimit(limit=10, window_seconds=60 * 60)
SEARCH = RateLimit(limit=120, window_seconds=60)
OUTBOUND_CLICK = RateLimit(limit=60, window_seconds=60)
COMPANY_REQUEST = RateLimit(limit=5, window_seconds=60 * 60)


async def enforce(bucket: str, identity: str, rule: RateLimit) -> None:
    """Raises RateLimitedError when `identity` exceeds `rule` in `bucket`."""
    if not settings.rate_limit_enabled:
        return
    redis = get_redis()
    key = f"rl:{bucket}:{rule.key_suffix}:{identity}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, rule.window_seconds)
    if count > rule.limit:
        ttl = await redis.ttl(key)
        raise RateLimitedError(details={"retry_after_seconds": max(ttl, 1)})
