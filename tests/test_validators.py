"""Tests for input validation helpers (validators.py)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from validators import (
    is_valid_email,
    is_valid_schedule_time,
    validate_csv_columns,
    validate_csv_row,
)


# ===================================================================
# is_valid_email
# ===================================================================

class TestIsValidEmail:
    """Tests for is_valid_email function."""

    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "first.last@example.com",
            "user+tag@example.com",
            "user-name@example.com",
            "user@sub.domain.co.kr",
        ],
        ids=["normal", "dots", "plus-tag", "hyphen", "subdomain"],
    )
    def test_valid_emails(self, email):
        assert is_valid_email(email) is True

    def test_valid_email_with_whitespace_trimmed(self):
        assert is_valid_email("  user@example.com  ") is True

    @pytest.mark.parametrize(
        "email",
        [
            "userexample.com",
            "user@",
            "@example.com",
            "",
            "user@.com",
            "user@example",
        ],
        ids=["no-at", "no-domain", "no-local", "empty", "dot-domain", "no-tld"],
    )
    def test_invalid_emails(self, email):
        assert is_valid_email(email) is False


# ===================================================================
# is_valid_schedule_time
# ===================================================================

class TestIsValidScheduleTime:
    """Tests for is_valid_schedule_time function."""

    @pytest.mark.parametrize(
        "time_str",
        [
            "00:00",
            "23:59",
            "12:30",
            "09:05",
        ],
        ids=["midnight", "end-of-day", "noon-ish", "morning"],
    )
    def test_valid_times(self, time_str):
        assert is_valid_schedule_time(time_str) is True

    def test_valid_time_with_whitespace_trimmed(self):
        assert is_valid_schedule_time("  14:30  ") is True

    @pytest.mark.parametrize(
        "time_str",
        [
            "24:00",
            "12:60",
            "9:05",
            "25:00",
            "",
            "12:0",
            "abc",
        ],
        ids=[
            "hour-24",
            "minute-60",
            "single-digit-hour",
            "hour-25",
            "empty",
            "single-digit-minute",
            "non-numeric",
        ],
    )
    def test_invalid_times(self, time_str):
        assert is_valid_schedule_time(time_str) is False


# ===================================================================
# validate_csv_columns
# ===================================================================

class TestValidateCsvColumns:
    """Tests for validate_csv_columns function."""

    def test_all_columns_present_returns_empty(self):
        columns = ["name", "email", "subject", "body"]
        assert validate_csv_columns(columns) == []

    def test_missing_single_column(self):
        columns = ["name", "email", "subject"]
        missing = validate_csv_columns(columns)
        assert missing == ["body"]

    def test_missing_multiple_columns(self):
        columns = ["name"]
        missing = validate_csv_columns(columns)
        assert sorted(missing) == ["body", "email", "subject"]

    def test_empty_column_list(self):
        missing = validate_csv_columns([])
        assert sorted(missing) == ["body", "email", "name", "subject"]

    def test_case_insensitive_matching(self):
        columns = ["Name", "EMAIL", "Subject", "BODY"]
        assert validate_csv_columns(columns) == []

    def test_whitespace_in_column_names_trimmed(self):
        columns = [" name ", " email", "subject ", " body "]
        assert validate_csv_columns(columns) == []

    def test_extra_columns_ignored(self):
        columns = ["name", "email", "subject", "body", "extra", "notes"]
        assert validate_csv_columns(columns) == []


# ===================================================================
# validate_csv_row
# ===================================================================

class TestValidateCsvRow:
    """Tests for validate_csv_row function."""

    def test_valid_row_returns_empty(self):
        row = {
            "name": "Alice",
            "email": "alice@example.com",
            "subject": "Hello",
            "body": "Content",
        }
        assert validate_csv_row(row, 1) == []

    def test_empty_name_produces_error(self):
        row = {
            "name": "",
            "email": "alice@example.com",
            "subject": "Hello",
            "body": "Content",
        }
        errors = validate_csv_row(row, 2)
        assert len(errors) == 1
        assert "name" in errors[0]

    def test_empty_email_produces_error(self):
        row = {
            "name": "Alice",
            "email": "",
            "subject": "Hello",
            "body": "Content",
        }
        errors = validate_csv_row(row, 3)
        assert len(errors) == 1
        assert "email" in errors[0]

    def test_invalid_email_format_produces_error(self):
        row = {
            "name": "Alice",
            "email": "not-valid",
            "subject": "Hello",
            "body": "Content",
        }
        errors = validate_csv_row(row, 4)
        assert any("잘못된 이메일 형식" in e for e in errors)

    def test_multiple_empty_fields_produce_multiple_errors(self):
        row = {
            "name": "",
            "email": "",
            "subject": "",
            "body": "",
        }
        errors = validate_csv_row(row, 5)
        assert len(errors) == 4

    def test_row_number_appears_in_error_message(self):
        row = {
            "name": "",
            "email": "alice@example.com",
            "subject": "Hello",
            "body": "Content",
        }
        errors = validate_csv_row(row, 42)
        assert all("행 42" in e for e in errors)

    def test_whitespace_only_field_treated_as_empty(self):
        row = {
            "name": "   ",
            "email": "alice@example.com",
            "subject": "Hello",
            "body": "Content",
        }
        errors = validate_csv_row(row, 1)
        assert len(errors) == 1
        assert "name" in errors[0]

    def test_missing_key_treated_as_empty(self):
        row = {
            "email": "alice@example.com",
            "subject": "Hello",
            "body": "Content",
        }
        errors = validate_csv_row(row, 7)
        assert len(errors) == 1
        assert "name" in errors[0]
