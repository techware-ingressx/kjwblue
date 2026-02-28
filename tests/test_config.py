"""Tests for environment variable loading (config.py)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_smtp_config


# ===================================================================
# load_smtp_config
# ===================================================================

class TestLoadSmtpConfig:
    """Tests for load_smtp_config function."""

    def test_valid_env_returns_smtp_config(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GMAIL_SENDER_EMAIL=user@gmail.com\n"
            "GMAIL_APP_PASSWORD=my-app-password\n",
            encoding="utf-8",
        )

        config = load_smtp_config(env_file=str(env_file))

        assert config.sender_email == "user@gmail.com"
        assert config.app_password == "my-app-password"
        assert config.host == "smtp.gmail.com"
        assert config.port == 587

    def test_extra_variables_are_ignored(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GMAIL_SENDER_EMAIL=user@gmail.com\n"
            "GMAIL_APP_PASSWORD=secret123\n"
            "SOME_OTHER_VAR=ignored\n",
            encoding="utf-8",
        )

        config = load_smtp_config(env_file=str(env_file))
        assert config.sender_email == "user@gmail.com"

    def test_empty_env_file_exits(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("", encoding="utf-8")

        with pytest.raises(SystemExit):
            load_smtp_config(env_file=str(env_file))

    def test_file_not_found_exits(self, tmp_path):
        missing_path = tmp_path / "nonexistent.env"

        with pytest.raises(SystemExit):
            load_smtp_config(env_file=str(missing_path))

    def test_missing_password_exits(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GMAIL_SENDER_EMAIL=user@gmail.com\n",
            encoding="utf-8",
        )

        with pytest.raises(SystemExit):
            load_smtp_config(env_file=str(env_file))
