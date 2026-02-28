"""Frozen Pydantic data models for email sending system."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class EmailRecord(BaseModel):
    """Single row from the email CSV file."""

    model_config = {"frozen": True}

    name: str = Field(min_length=1)
    email: EmailStr
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)


class SendResult(BaseModel):
    """Result of a single email send attempt."""

    model_config = {"frozen": True}

    name: str
    email: str
    subject: str
    status: str = Field(pattern=r"^(success|failure)$")
    timestamp: datetime
    error_message: str = ""


class SmtpConfig(BaseModel):
    """SMTP connection configuration."""

    model_config = {"frozen": True}

    host: str = "smtp.gmail.com"
    port: int = 587
    sender_email: str
    app_password: str


class RateLimitState(BaseModel):
    """Immutable snapshot of rate limiter state."""

    model_config = {"frozen": True}

    sent_count: int = 0
    daily_limit: int = 450
    interval_seconds: float = 1.0
    last_sent_at: float = 0.0

    @property
    def can_send(self) -> bool:
        return self.sent_count < self.daily_limit

    @property
    def remaining(self) -> int:
        return max(0, self.daily_limit - self.sent_count)
