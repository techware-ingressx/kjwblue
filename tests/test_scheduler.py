"""Tests for scheduled email sending (scheduler.py)."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scheduler import calculate_wait_description, schedule_send


# ===================================================================
# calculate_wait_description
# ===================================================================

class TestCalculateWaitDescription:
    """Tests for calculate_wait_description function."""

    @patch("scheduler.datetime")
    def test_future_time_shows_hours_and_minutes(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 3, 1, 10, 0, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        result = calculate_wait_description("13:30")

        assert "3시간" in result
        assert "30분" in result

    @patch("scheduler.datetime")
    def test_past_time_shows_next_day(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 3, 1, 15, 0, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        result = calculate_wait_description("10:00")

        assert "2026-03-02" in result

    @patch("scheduler.datetime")
    def test_format_contains_target_datetime(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 3, 1, 8, 0, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        result = calculate_wait_description("14:30")

        assert "2026-03-01 14:30" in result

    @patch("scheduler.datetime")
    def test_minutes_only_when_under_one_hour(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 3, 1, 10, 0, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        result = calculate_wait_description("10:45")

        assert "시간" not in result
        assert "45분" in result

    @patch("scheduler.datetime")
    def test_same_time_shows_next_day(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 3, 1, 10, 30, 1)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        result = calculate_wait_description("10:30")

        assert "2026-03-02" in result


# ===================================================================
# schedule_send
# ===================================================================

class TestScheduleSend:
    """Tests for schedule_send function."""

    @patch("scheduler.sys.exit")
    def test_invalid_time_exits(self, mock_exit):
        mock_exit.side_effect = SystemExit(1)
        send_fn = MagicMock()

        with pytest.raises(SystemExit):
            schedule_send("25:00", send_fn)

        mock_exit.assert_called_once_with(1)
        send_fn.assert_not_called()

    @patch("scheduler.time.sleep")
    @patch("scheduler.schedule")
    @patch("scheduler.calculate_wait_description", return_value="test desc")
    def test_callback_executed(self, mock_desc, mock_schedule, mock_sleep):
        send_fn = MagicMock()
        job_mock = MagicMock()
        mock_schedule.every.return_value.day.at.return_value.do = job_mock

        call_count = 0

        def fake_run_pending():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                captured_fn = job_mock.call_args[0][0]
                captured_fn()

        mock_schedule.run_pending = fake_run_pending

        schedule_send("10:30", send_fn)

        send_fn.assert_called_once()

    @patch("scheduler.time.sleep")
    @patch("scheduler.schedule")
    @patch("scheduler.calculate_wait_description", return_value="test desc")
    @patch("scheduler.sys.exit")
    def test_keyboard_interrupt_exits_cleanly(
        self, mock_exit, mock_desc, mock_schedule, mock_sleep,
    ):
        mock_exit.side_effect = SystemExit(0)
        send_fn = MagicMock()
        job_mock = MagicMock()
        mock_schedule.every.return_value.day.at.return_value.do = job_mock
        mock_schedule.run_pending.side_effect = KeyboardInterrupt

        with pytest.raises(SystemExit):
            schedule_send("10:30", send_fn)

        mock_schedule.clear.assert_called()
        mock_exit.assert_called_once_with(0)
        send_fn.assert_not_called()

    @patch("scheduler.time.sleep")
    @patch("scheduler.schedule")
    @patch("scheduler.calculate_wait_description", return_value="test desc")
    def test_schedule_registered_with_correct_time(
        self, mock_desc, mock_schedule, mock_sleep,
    ):
        send_fn = MagicMock()
        job_mock = MagicMock()
        mock_schedule.every.return_value.day.at.return_value.do = job_mock

        call_count = 0

        def fake_run_pending():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                captured_fn = job_mock.call_args[0][0]
                captured_fn()

        mock_schedule.run_pending = fake_run_pending

        schedule_send("14:00", send_fn)

        mock_schedule.every.return_value.day.at.assert_called_with("14:00")
