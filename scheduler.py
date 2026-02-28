"""Scheduled email sending."""

import sys
import time
from datetime import datetime, timedelta
from typing import Callable

import schedule

from validators import is_valid_schedule_time


def calculate_wait_description(target_time: str) -> str:
    """Calculate and return a description of when the job will run."""
    now = datetime.now()
    hour, minute = map(int, target_time.split(":"))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target <= now:
        target = target + timedelta(days=1)

    diff = target - now
    hours, remainder = divmod(int(diff.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)

    if hours > 0:
        return f"{target.strftime('%Y-%m-%d %H:%M')} (약 {hours}시간 {minutes}분 후)"
    return f"{target.strftime('%Y-%m-%d %H:%M')} (약 {minutes}분 후)"


def schedule_send(target_time: str, send_fn: Callable[[], None]) -> None:
    """Schedule email sending at the specified HH:MM time.

    Runs once then exits. If the time has already passed today,
    it will run at that time tomorrow.
    """
    if not is_valid_schedule_time(target_time):
        print(f"[ERROR] 잘못된 시간 형식: '{target_time}' (HH:MM 형식 필요)", file=sys.stderr)
        sys.exit(1)

    executed = False

    def run_once() -> None:
        nonlocal executed
        if not executed:
            executed = True
            send_fn()
            schedule.clear()

    description = calculate_wait_description(target_time)
    print(f"[예약] {description}에 발송 예정")
    print("[예약] Ctrl+C로 취소할 수 있습니다")

    schedule.every().day.at(target_time).do(run_once)

    try:
        while not executed:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[취소] 예약 발송이 취소되었습니다")
        schedule.clear()
        sys.exit(0)
