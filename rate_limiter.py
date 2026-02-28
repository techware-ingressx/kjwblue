"""Gmail rate limiting with immutable state."""

import time

from models import RateLimitState


def create_rate_limiter(
    daily_limit: int = 450,
    interval_seconds: float = 1.0,
) -> RateLimitState:
    """Create a new rate limiter state."""
    return RateLimitState(
        daily_limit=daily_limit,
        interval_seconds=interval_seconds,
    )


def wait_if_needed(state: RateLimitState) -> RateLimitState:
    """Wait for the rate limit interval if needed.

    Returns a new state with updated last_sent_at timestamp.
    """
    if not state.can_send:
        raise RuntimeError(
            f"일일 발송 한도({state.daily_limit}통) 초과"
        )

    now = time.monotonic()
    elapsed = now - state.last_sent_at

    if state.last_sent_at > 0 and elapsed < state.interval_seconds:
        time.sleep(state.interval_seconds - elapsed)

    return RateLimitState(
        sent_count=state.sent_count + 1,
        daily_limit=state.daily_limit,
        interval_seconds=state.interval_seconds,
        last_sent_at=time.monotonic(),
    )
