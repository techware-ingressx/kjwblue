"""Input validation helpers."""

import re


EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

REQUIRED_CSV_COLUMNS = frozenset({"name", "email", "subject", "body"})


def is_valid_email(email: str) -> bool:
    """Check if email address has valid format."""
    return bool(EMAIL_PATTERN.match(email.strip()))


def is_valid_schedule_time(time_str: str) -> bool:
    """Check if time string is valid HH:MM format (24-hour)."""
    return bool(TIME_PATTERN.match(time_str.strip()))


def validate_csv_columns(columns: list[str]) -> list[str]:
    """Validate CSV has all required columns.

    Returns list of missing column names (empty if all present).
    """
    normalized = {col.strip().lower() for col in columns}
    missing = REQUIRED_CSV_COLUMNS - normalized
    return sorted(missing)


def validate_csv_row(row: dict[str, str], row_number: int) -> list[str]:
    """Validate a single CSV row.

    Returns list of error messages (empty if valid).
    """
    errors = []

    for field in REQUIRED_CSV_COLUMNS:
        value = row.get(field, "").strip()
        if not value:
            errors.append(f"행 {row_number}: '{field}' 값이 비어있습니다")

    email = row.get("email", "").strip()
    if email and not is_valid_email(email):
        errors.append(f"행 {row_number}: 잘못된 이메일 형식 '{email}'")

    return errors
