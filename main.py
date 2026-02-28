"""CLI entry point for email CSV sender."""

import argparse
import sys
from datetime import datetime

from config import load_smtp_config
from csv_reader import read_email_csv
from rate_limiter import create_rate_limiter
from scheduler import schedule_send
from send_logger import format_summary
from smtp_sender import send_all_emails


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CSV 파일로 HTML 이메일을 자동 발송합니다.",
    )
    parser.add_argument(
        "csv_file",
        help="발송할 이메일 목록 CSV 파일 경로",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="CSV 검증만 수행 (발송하지 않음)",
    )
    parser.add_argument(
        "--schedule",
        metavar="HH:MM",
        help="지정 시간에 발송 (24시간 형식, 예: 10:30)",
    )
    parser.add_argument(
        "--log-path",
        default=None,
        help="발송 로그 CSV 경로 (기본: send_log_YYYYMMDD_HHMMSS.csv)",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="CSV 파일 인코딩 (기본: utf-8)",
    )
    return parser


def default_log_path() -> str:
    return f"send_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def run_send(csv_file: str, log_path: str, encoding: str) -> None:
    """Execute the email sending pipeline."""
    smtp_config = load_smtp_config()

    csv_result = read_email_csv(csv_file, encoding=encoding)

    if csv_result.has_errors:
        print("\n[경고] CSV 검증 오류:")
        for err in csv_result.errors:
            print(f"  - {err}")

    if not csv_result.records:
        print("[ERROR] 발송할 유효한 이메일이 없습니다.", file=sys.stderr)
        sys.exit(1)

    print(f"\n[발송 시작] {csv_result.summary}")
    print(f"[발신자] {smtp_config.sender_email}")
    print(f"[로그] {log_path}\n")

    rate_state = create_rate_limiter()
    results = send_all_emails(csv_result.records, smtp_config, log_path, rate_state)

    print(f"\n{format_summary(results)}")
    print(f"[로그 저장] {log_path}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    log_path = args.log_path or default_log_path()

    csv_result = read_email_csv(args.csv_file, encoding=args.encoding)

    if csv_result.has_errors:
        print("\n[경고] CSV 검증 오류:")
        for err in csv_result.errors:
            print(f"  - {err}")

    if args.dry_run:
        print(f"\n[DRY-RUN] {csv_result.summary}")
        if csv_result.records:
            print("\n미리보기:")
            for i, r in enumerate(csv_result.records, start=1):
                print(f"  {i}. {r.name} <{r.email}> - {r.subject}")
        if not csv_result.records:
            sys.exit(1)
        return

    if not csv_result.records:
        print("[ERROR] 발송할 유효한 이메일이 없습니다.", file=sys.stderr)
        sys.exit(1)

    if args.schedule:
        schedule_send(
            args.schedule,
            lambda: run_send(args.csv_file, log_path, args.encoding),
        )
    else:
        run_send(args.csv_file, log_path, args.encoding)


if __name__ == "__main__":
    main()
