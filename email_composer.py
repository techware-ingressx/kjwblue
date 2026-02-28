"""HTML email composition with MIME."""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from models import EmailRecord


def personalize_body(body: str, name: str) -> str:
    """Replace {name} placeholders with the recipient's name."""
    return body.replace("{name}", name)


def compose_email(
    record: EmailRecord,
    sender_email: str,
) -> MIMEMultipart:
    """Create a MIME email message from an EmailRecord.

    Personalizes {name} in both subject and body.
    """
    personalized_subject = personalize_body(record.subject, record.name)
    personalized_body = personalize_body(record.body, record.name)

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = record.email
    msg["Subject"] = personalized_subject

    html_part = MIMEText(personalized_body, "html", "utf-8")
    msg.attach(html_part)

    return msg
