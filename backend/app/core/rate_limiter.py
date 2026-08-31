import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import HTTPException, Request, Response, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """
    Thread-safe, sliding-window in-memory rate limiter.
    Maintains timestamped hit logs partitioned by client identifier (IP or User ID) and tier key.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # map: key -> list of float timestamps (epoch seconds)
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int, int]:
        """
        Check if request is allowed under the rate limit.

        Returns:
            (allowed: bool, limit: int, remaining: int, retry_after: int)
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            timestamps = self._hits[key]
            # Prune timestamps older than window_start
            valid_timestamps = [ts for ts in timestamps if ts > window_start]
            self._hits[key] = valid_timestamps

            count = len(valid_timestamps)
            if count >= limit:
                # Oldest timestamp in current window defines retry_after
                oldest = valid_timestamps[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                return False, limit, 0, retry_after

            # Record current hit
            valid_timestamps.append(now)
            remaining = max(0, limit - len(valid_timestamps))
            return True, limit, remaining, 0

    def reset(self) -> None:
        """Clear all rate limit windows (used for test isolation)."""
        with self._lock:
            self._hits.clear()


# Global in-memory rate limiter instance
rate_limiter = SlidingWindowRateLimiter()


def get_client_identifier(request: Request) -> str:
    """Extract authoritative client IP or forwarded IP for rate limiting."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip

    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def create_rate_limit_dependency(
    tier_name: str,
    limit_getter: Callable[[], int],
    window_seconds: int = 60,
) -> Callable:
    """Factory returning a FastAPI dependency enforcing sliding-window rate limiting."""

    async def _rate_limit_check(request: Request, response: Response) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return

        client_id = get_client_identifier(request)
        limit = limit_getter()
        key = f"{tier_name}:{client_id}"

        allowed, max_limit, remaining, retry_after = rate_limiter.is_allowed(
            key=key,
            limit=limit,
            window_seconds=window_seconds,
        )

        response.headers["X-RateLimit-Limit"] = str(max_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(window_seconds)

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                extra={
                    "tier": tier_name,
                    "client_id": client_id,
                    "limit": max_limit,
                    "retry_after": retry_after,
                },
            )
            response.headers["Retry-After"] = str(retry_after)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {tier_name}. Maximum {max_limit} requests per {window_seconds}s. Retry after {retry_after}s.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
            )

    return _rate_limit_check


# Pre-configured rate limiting dependencies
rate_limit_auth = create_rate_limit_dependency(
    "auth", lambda: get_settings().rate_limit_auth_per_minute, 60
)
rate_limit_webhooks = create_rate_limit_dependency(
    "webhooks", lambda: get_settings().rate_limit_webhooks_per_minute, 60
)
rate_limit_mutations = create_rate_limit_dependency(
    "mutations", lambda: get_settings().rate_limit_mutations_per_minute, 60
)
rate_limit_reads = create_rate_limit_dependency(
    "reads", lambda: get_settings().rate_limit_reads_per_minute, 60
)
