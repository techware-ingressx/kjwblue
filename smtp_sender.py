"""SMTP email sending with retry and rate limiting."""

import smtplib
import ssl
import time
from datetime import datetime

from email_composer import compose_email
from models import EmailRecord, RateLimitState, SendResult, SmtpConfig
from rate_limiter import wait_if_needed
from send_logger import append_result


def send_single_email(
    record: EmailRecord,
    smtp_config: SmtpConfig,
    connection: smtplib.SMTP,
) -> SendResult:
    """Send a single email. Returns SendResult instead of raising."""
    try:
        msg = compose_email(record, smtp_config.sender_email)
        connection.sendmail(
            smtp_config.sender_email,
            record.email,
            msg.as_string(),
        )
        return SendResult(
            name=record.name,
            email=record.email,
            subject=record.subject,
            status="success",
            timestamp=datetime.now(),
        )
    except smtplib.SMTPRecipientsRefused as e:
        return SendResult(
            name=record.name,
            email=record.email,
            subject=record.subject,
            status="failure",
            timestamp=datetime.now(),
            error_message=f"수신 거부: {e}",
        )
    except Exception as e:
        return SendResult(
            name=record.name,
            email=record.email,
            subject=record.subject,
            status="failure",
            timestamp=datetime.now(),
            error_message=str(e),
        )


def send_with_retry(
    record: EmailRecord,
    smtp_config: SmtpConfig,
    connection: smtplib.SMTP,
    max_retries: int = 3,
) -> SendResult:
    """Send with retry for transient errors."""
    last_result = None

    for attempt in range(max_retries):
        result = send_single_email(record, smtp_config, connection)

        if result.status == "success":
            return result

        last_result = result

        if attempt < max_retries - 1:
            wait_seconds = 2 ** attempt
            print(f"  재시도 {attempt + 1}/{max_retries - 1} ({wait_seconds}초 후)...")
            time.sleep(wait_seconds)

    return last_result


def create_smtp_connection(smtp_config: SmtpConfig) -> smtplib.SMTP:
    """Create and authenticate an SMTP connection."""
    context = ssl.create_default_context()
    connection = smtplib.SMTP(smtp_config.host, smtp_config.port)
    connection.starttls(context=context)
    connection.login(smtp_config.sender_email, smtp_config.app_password)
    return connection


def send_all_emails(
    records: tuple[EmailRecord, ...],
    smtp_config: SmtpConfig,
    log_path: str,
    rate_state: RateLimitState,
) -> tuple[SendResult, ...]:
    """Send all emails with rate limiting and logging.

    Returns tuple of all SendResults.
    """
    results: list[SendResult] = []

    try:
        connection = create_smtp_connection(smtp_config)
    except Exception as e:
        print(f"[ERROR] SMTP 연결 실패: {e}")
        error_results = tuple(
            SendResult(
                name=r.name,
                email=r.email,
                subject=r.subject,
                status="failure",
                timestamp=datetime.now(),
                error_message=f"SMTP 연결 실패: {e}",
            )
            for r in records
        )
        for result in error_results:
            append_result(log_path, result)
        return error_results

    current_state = rate_state

    try:
        for i, record in enumerate(records, start=1):
            if not current_state.can_send:
                print(f"[경고] 일일 발송 한도 도달 ({current_state.daily_limit}통)")
                remaining = records[i - 1:]
                for r in remaining:
                    result = SendResult(
                        name=r.name,
                        email=r.email,
                        subject=r.subject,
                        status="failure",
                        timestamp=datetime.now(),
                        error_message="일일 발송 한도 초과",
                    )
                    results.append(result)
                    append_result(log_path, result)
                break

            current_state = wait_if_needed(current_state)

            print(f"[{i}/{len(records)}] {record.email} 발송 중...")
            result = send_with_retry(record, smtp_config, connection)
            results.append(result)
            append_result(log_path, result)

            if result.status == "success":
                print(f"  -> 성공")
            else:
                print(f"  -> 실패: {result.error_message}")
    finally:
        try:
            connection.quit()
        except Exception:
            pass

    return tuple(results)
