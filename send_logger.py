"""Send result logging to CSV."""

import csv
from pathlib import Path

from models import SendResult


CSV_COLUMNS = ("timestamp", "name", "email", "subject", "status", "error_message")


def write_log_header(log_path: str) -> None:
    """Write CSV header if the log file doesn't exist yet."""
    path = Path(log_path)
    if not path.exists():
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)


def append_result(log_path: str, result: SendResult) -> None:
    """Append a single send result to the log CSV."""
    write_log_header(log_path)

    with open(log_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow((
            result.timestamp.isoformat(),
            result.name,
            result.email,
            result.subject,
            result.status,
            result.error_message,
        ))


def append_results(log_path: str, results: tuple[SendResult, ...]) -> None:
    """Append multiple send results to the log CSV."""
    write_log_header(log_path)

    with open(log_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for result in results:
            writer.writerow((
                result.timestamp.isoformat(),
                result.name,
                result.email,
                result.subject,
                result.status,
                result.error_message,
            ))


def format_summary(results: tuple[SendResult, ...]) -> str:
    """Format a human-readable summary of send results."""
    success = sum(1 for r in results if r.status == "success")
    failure = len(results) - success
    return f"발송 완료: 성공 {success}건, 실패 {failure}건 (총 {len(results)}건)"
