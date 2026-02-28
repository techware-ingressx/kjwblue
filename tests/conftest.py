"""Shared fixtures for email CSV sending system tests."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import EmailRecord, RateLimitState, SendResult, SmtpConfig


# ---------------------------------------------------------------------------
# EmailRecord fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_record() -> EmailRecord:
    """Single valid EmailRecord."""
    return EmailRecord(
        name="Alice Kim",
        email="alice@example.com",
        subject="Welcome",
        body="Hello Alice, welcome aboard!",
    )


@pytest.fixture()
def sample_records() -> tuple[EmailRecord, ...]:
    """Tuple of 3 valid EmailRecords."""
    return (
        EmailRecord(
            name="Alice Kim",
            email="alice@example.com",
            subject="Welcome",
            body="Hello Alice!",
        ),
        EmailRecord(
            name="Bob Park",
            email="bob@example.com",
            subject="Update",
            body="Hi Bob, here is your update.",
        ),
        EmailRecord(
            name="Carol Lee",
            email="carol@example.com",
            subject="Reminder",
            body="Dear Carol, a quick reminder.",
        ),
    )


# ---------------------------------------------------------------------------
# SmtpConfig fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def smtp_config() -> SmtpConfig:
    """SmtpConfig with test values."""
    return SmtpConfig(
        sender_email="test@example.com",
        app_password="test-app-password-123",
    )


# ---------------------------------------------------------------------------
# SendResult fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def success_result() -> SendResult:
    """Successful SendResult."""
    return SendResult(
        name="Alice Kim",
        email="alice@example.com",
        subject="Welcome",
        status="success",
        timestamp=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def failure_result() -> SendResult:
    """Failed SendResult with error message."""
    return SendResult(
        name="Bob Park",
        email="bob@example.com",
        subject="Update",
        status="failure",
        timestamp=datetime(2026, 1, 15, 10, 31, 0, tzinfo=timezone.utc),
        error_message="SMTP connection refused",
    )


@pytest.fixture()
def mixed_results(success_result, failure_result) -> tuple[SendResult, ...]:
    """Tuple containing both success and failure results."""
    return (
        success_result,
        failure_result,
        SendResult(
            name="Carol Lee",
            email="carol@example.com",
            subject="Reminder",
            status="success",
            timestamp=datetime(2026, 1, 15, 10, 32, 0, tzinfo=timezone.utc),
        ),
    )


# ---------------------------------------------------------------------------
# RateLimitState fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def rate_state() -> RateLimitState:
    """Default RateLimitState."""
    return RateLimitState()


# ---------------------------------------------------------------------------
# Mock SMTP connection
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_smtp_connection() -> MagicMock:
    """MagicMock SMTP connection where sendmail succeeds."""
    mock = MagicMock()
    mock.sendmail.return_value = {}
    mock.ehlo.return_value = (250, b"OK")
    mock.starttls.return_value = (220, b"Ready")
    mock.login.return_value = (235, b"Accepted")
    return mock


# ---------------------------------------------------------------------------
# CSV fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def valid_csv_content() -> str:
    """CSV string with headers and 3 data rows."""
    return (
        "name,email,subject,body\n"
        "Alice Kim,alice@example.com,Welcome,Hello Alice!\n"
        "Bob Park,bob@example.com,Update,Hi Bob here is your update.\n"
        "Carol Lee,carol@example.com,Reminder,Dear Carol a quick reminder.\n"
    )


@pytest.fixture()
def valid_csv_path(tmp_path, valid_csv_content) -> Path:
    """Temporary CSV file with valid content."""
    csv_file = tmp_path / "test_emails.csv"
    csv_file.write_text(valid_csv_content, encoding="utf-8")
    return csv_file
