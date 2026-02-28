"""Tests for rate_limiter module."""

from unittest.mock import patch

import pytest

from models import RateLimitState
from rate_limiter import create_rate_limiter, wait_if_needed


# ---------------------------------------------------------------------------
# create_rate_limiter
# ---------------------------------------------------------------------------


class TestCreateRateLimiter:
    """Tests for create_rate_limiter function."""

    def test_default_daily_limit(self):
        state = create_rate_limiter()

        assert state.daily_limit == 450

    def test_default_interval_seconds(self):
        state = create_rate_limiter()

        assert state.interval_seconds == 1.0

    def test_custom_daily_limit(self):
        state = create_rate_limiter(daily_limit=100)

        assert state.daily_limit == 100

    def test_custom_interval_seconds(self):
        state = create_rate_limiter(interval_seconds=2.5)

        assert state.interval_seconds == 2.5

    def test_initial_sent_count_is_zero(self):
        state = create_rate_limiter()

        assert state.sent_count == 0

    def test_initial_last_sent_at_is_zero(self):
        state = create_rate_limiter()

        assert state.last_sent_at == 0.0

    def test_returns_rate_limit_state(self):
        state = create_rate_limiter()

        assert isinstance(state, RateLimitState)


# ---------------------------------------------------------------------------
# wait_if_needed
# ---------------------------------------------------------------------------


class TestWaitIfNeeded:
    """Tests for wait_if_needed function."""

    @patch("rate_limiter.time")
    def test_first_call_no_sleep(self, mock_time):
        mock_time.monotonic.return_value = 100.0
        state = RateLimitState(last_sent_at=0.0)

        wait_if_needed(state)

        mock_time.sleep.assert_not_called()

    @patch("rate_limiter.time")
    def test_interval_not_met_triggers_sleep(self, mock_time):
        mock_time.monotonic.return_value = 10.3
        state = RateLimitState(last_sent_at=10.0, interval_seconds=1.0)

        wait_if_needed(state)

        mock_time.sleep.assert_called_once_with(pytest.approx(0.7, abs=0.01))

    @patch("rate_limiter.time")
    def test_interval_met_no_sleep(self, mock_time):
        mock_time.monotonic.return_value = 12.0
        state = RateLimitState(last_sent_at=10.0, interval_seconds=1.0)

        wait_if_needed(state)

        mock_time.sleep.assert_not_called()

    @patch("rate_limiter.time")
    def test_returns_new_state_with_incremented_count(self, mock_time):
        mock_time.monotonic.return_value = 100.0
        state = RateLimitState(sent_count=5)

        new_state = wait_if_needed(state)

        assert new_state.sent_count == 6

    @patch("rate_limiter.time")
    def test_returns_new_state_preserves_limits(self, mock_time):
        mock_time.monotonic.return_value = 100.0
        state = RateLimitState(daily_limit=200, interval_seconds=2.0)

        new_state = wait_if_needed(state)

        assert new_state.daily_limit == 200
        assert new_state.interval_seconds == 2.0

    @patch("rate_limiter.time")
    def test_returns_new_state_updates_last_sent_at(self, mock_time):
        mock_time.monotonic.return_value = 42.0
        state = RateLimitState()

        new_state = wait_if_needed(state)

        assert new_state.last_sent_at == 42.0

    def test_limit_exceeded_raises_runtime_error(self):
        state = RateLimitState(sent_count=450, daily_limit=450)

        with pytest.raises(RuntimeError, match="일일 발송 한도"):
            wait_if_needed(state)

    @patch("rate_limiter.time")
    def test_returns_new_object_not_same_reference(self, mock_time):
        mock_time.monotonic.return_value = 100.0
        state = RateLimitState()

        new_state = wait_if_needed(state)

        assert new_state is not state

    @patch("rate_limiter.time")
    def test_original_state_unchanged_after_call(self, mock_time):
        mock_time.monotonic.return_value = 100.0
        state = RateLimitState(sent_count=3, daily_limit=450)

        wait_if_needed(state)

        assert state.sent_count == 3
        assert state.daily_limit == 450
