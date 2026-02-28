"""Tests for email_composer module."""

import pytest
from email.mime.multipart import MIMEMultipart

from email_composer import compose_email, personalize_body
from models import EmailRecord


# ---------------------------------------------------------------------------
# personalize_body
# ---------------------------------------------------------------------------


class TestPersonalizeBody:
    """Tests for personalize_body function."""

    def test_single_placeholder_replaced(self):
        result = personalize_body("Hello {name}!", "Alice")

        assert result == "Hello Alice!"

    def test_multiple_placeholders_replaced(self):
        result = personalize_body(
            "Dear {name}, welcome {name}!", "Bob"
        )

        assert result == "Dear Bob, welcome Bob!"

    def test_no_placeholder_returns_unchanged(self):
        body = "Hello there, welcome aboard!"

        result = personalize_body(body, "Alice")

        assert result == body

    def test_empty_name_replaces_with_empty(self):
        result = personalize_body("Hello {name}!", "")

        assert result == "Hello !"

    @pytest.mark.parametrize(
        ("body", "name", "expected"),
        [
            ("{name}", "Alice", "Alice"),
            ("<h1>{name}</h1>", "Bob", "<h1>Bob</h1>"),
            ("{name}{name}", "X", "XX"),
        ],
        ids=["only-placeholder", "html-wrapped", "adjacent-placeholders"],
    )
    def test_various_placeholder_positions(self, body, name, expected):
        result = personalize_body(body, name)

        assert result == expected


# ---------------------------------------------------------------------------
# compose_email
# ---------------------------------------------------------------------------


class TestComposeEmail:
    """Tests for compose_email function."""

    def test_from_header_set(self, sample_record):
        msg = compose_email(sample_record, "sender@example.com")

        assert msg["From"] == "sender@example.com"

    def test_to_header_set(self, sample_record):
        msg = compose_email(sample_record, "sender@example.com")

        assert msg["To"] == sample_record.email

    def test_subject_header_set(self, sample_record):
        msg = compose_email(sample_record, "sender@example.com")

        assert msg["Subject"] == sample_record.subject

    def test_subject_personalized_with_name(self):
        record = EmailRecord(
            name="Dana",
            email="dana@example.com",
            subject="Hello {name}",
            body="Body content",
        )

        msg = compose_email(record, "sender@example.com")

        assert msg["Subject"] == "Hello Dana"

    def test_body_personalized_in_html_payload(self):
        record = EmailRecord(
            name="Eve",
            email="eve@example.com",
            subject="Subject",
            body="<p>Welcome {name}</p>",
        )

        msg = compose_email(record, "sender@example.com")
        payload = msg.get_payload()
        html_part = payload[0]

        assert "Welcome Eve" in html_part.get_payload(decode=True).decode("utf-8")

    def test_mime_type_is_html(self, sample_record):
        msg = compose_email(sample_record, "sender@example.com")
        payload = msg.get_payload()
        html_part = payload[0]

        assert html_part.get_content_type() == "text/html"

    def test_returns_mime_multipart(self, sample_record):
        msg = compose_email(sample_record, "sender@example.com")

        assert isinstance(msg, MIMEMultipart)
