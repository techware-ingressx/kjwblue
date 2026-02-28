"""Environment variable loading via pydantic-settings."""

import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from models import SmtpConfig


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gmail_sender_email: str
    gmail_app_password: str


def load_smtp_config(env_file: str = ".env") -> SmtpConfig:
    """Load SMTP configuration from environment variables.

    Returns SmtpConfig on success, exits with error message on failure.
    """
    try:
        settings = AppSettings(_env_file=Path(env_file))
    except Exception as e:
        print(f"[ERROR] 환경변수 로딩 실패: {e}", file=sys.stderr)
        print("  .env 파일에 GMAIL_SENDER_EMAIL, GMAIL_APP_PASSWORD를 설정하세요.", file=sys.stderr)
        sys.exit(1)

    return SmtpConfig(
        sender_email=settings.gmail_sender_email,
        app_password=settings.gmail_app_password,
    )
