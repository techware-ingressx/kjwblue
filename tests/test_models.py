"""Tests for Pydantic data models (models.py)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import EmailRecord, RateLimitState, SendResult, SmtpConfig


# ===================================================================
# EmailRecord
# ===================================================================

class TestEmailRecord:
    """Tests for EmailRecord model."""

    def test_valid_creation(self, sample_record):
        assert sample_record.name == "Alice Kim"
        assert sample_record.email == "alice@example.com"
        assert sample_record.subject == "Welcome"
        assert sample_record.body == "Hello Alice, welcome aboard!"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            EmailRecord(
                name="",
                email="test@example.com",
                subject="Subject",
                body="Body text",
            )

    def test_empty_subject_rejected(self):
        with pytest.raises(ValidationError):
            EmailRecord(
                name="Test User",
                email="test@example.com",
                subject="",
                body="Body text",
            )

    def test_empty_body_rejected(self):
        with pytest.raises(ValidationError):
            EmailRecord(
                name="Test User",
                email="test@example.com",
                subject="Subject",
                body="",
            )

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            EmailRecord(
                name="Test User",
                email="not-an-email",
                subject="Subject",
                body="Body text",
            )

    def test_frozen_model_rejects_mutation(self, sample_record):
        with pytest.raises(ValidationError):
            sample_record.name = "Changed Name"


# ===================================================================
# SendResult
# ===================================================================

class TestSendResult:
    """Tests for SendResult model."""

    def test_success_creation(self, success_result):
        assert success_result.status == "success"
        assert success_result.error_message == ""

    def test_failure_creation(self, failure_result):
        assert failure_result.status == "failure"
        assert failure_result.error_message == "SMTP connection refused"

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            SendResult(
                name="Test",
                email="test@example.com",
                subject="Subject",
                status="pending",
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

    def test_default_error_message_is_empty(self, success_result):
        assert success_result.error_message == ""

    def test_frozen_model_rejects_mutation(self, success_result):
        with pytest.raises(ValidationError):
            success_result.status = "failure"


# ===================================================================
# SmtpConfig
# ===================================================================

class TestSmtpConfig:
    """Tests for SmtpConfig model."""

    def test_default_host_and_port(self, smtp_config):
        assert smtp_config.host == "smtp.gmail.com"
        assert smtp_config.port == 587

    def test_custom_host_and_port(self):
        config = SmtpConfig(
            host="mail.custom.com",
            port=465,
            sender_email="user@custom.com",
            app_password="secret",
        )
        assert config.host == "mail.custom.com"
        assert config.port == 465

    def test_sender_email_stored(self, smtp_config):
        assert smtp_config.sender_email == "test@example.com"

    def test_frozen_model_rejects_mutation(self, smtp_config):
        with pytest.raises(ValidationError):
            smtp_config.host = "other.host.com"


# ===================================================================
# RateLimitState
# ===================================================================

class TestRateLimitState:
    """Tests for RateLimitState model."""

    def test_default_values(self, rate_state):
        assert rate_state.sent_count == 0
        assert rate_state.daily_limit == 450
        assert rate_state.interval_seconds == 1.0
        assert rate_state.last_sent_at == 0.0

    def test_can_send_when_under_limit(self, rate_state):
        assert rate_state.can_send is True

    def test_remaining_at_default(self, rate_state):
        assert rate_state.remaining == 450

    def test_can_send_false_when_limit_reached(self):
        state = RateLimitState(sent_count=450, daily_limit=450)
        assert state.can_send is False

    def test_remaining_zero_when_limit_reached(self):
        state = RateLimitState(sent_count=450, daily_limit=450)
        assert state.remaining == 0

    def test_remaining_never_negative(self):
        state = RateLimitState(sent_count=500, daily_limit=450)
        assert state.remaining == 0

    def test_can_send_with_partial_usage(self):
        state = RateLimitState(sent_count=200, daily_limit=450)
        assert state.can_send is True
        assert state.remaining == 250
