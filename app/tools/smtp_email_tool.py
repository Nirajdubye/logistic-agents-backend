import os
import re
import smtplib
import ssl
from datetime import datetime, timezone
import email.charset
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import certifi
from dotenv import load_dotenv

load_dotenv()

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SMTP_HOST = os.getenv("SMTP_SERVER", os.getenv("SMTP_HOST", "smtp.gmail.com"))
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SMTP_EMAIL") or os.getenv("EMAIL_ADDRESS")
SENDER_APP_PASSWORD = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_APP_PASSWORD")

MAX_BODY_CHARS = 100000  # sanity cap - guard against runaway tokens

# UTF-8 charset configured with Quoted-Printable transfer encoding
utf8_qp = email.charset.Charset("utf-8")
utf8_qp.body_encoding = email.charset.QP


def _create_utf8_text(text: str, subtype: str = "plain") -> MIMEText:
    return MIMEText(text, subtype, _charset=utf8_qp)


def _validate_email(address: str) -> str | None:
    """Returns an error message if invalid, or None if the address looks OK."""
    if not address or not EMAIL_REGEX.match(address.strip()):
        return f"'{address}' does not look like a valid email address."
    return None


def send_email_smtp(
    recipient_email: str,
    subject: str,
    body: str,
    body_html: str | None = None,
    inline_images: list[dict] | None = None,
) -> dict:
    """
    Sends one email via SMTP.
    Returns a result dict - always returns a dict, never raises unhandled exceptions.
    """
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        return {
            "status": "error",
            "message": (
                "Email is not configured on the server. Set SMTP_EMAIL and "
                "SMTP_PASSWORD in .env before sending is possible."
            ),
        }

    error = _validate_email(recipient_email)
    if error:
        return {"status": "error", "message": error}

    if not subject or not subject.strip():
        return {"status": "error", "message": "Email subject cannot be empty."}
    if not body or not body.strip():
        return {"status": "error", "message": "Email plain-text body cannot be empty (required even when body_html is provided, as a fallback)."}
    if len(body) > MAX_BODY_CHARS or (body_html and len(body_html) > MAX_BODY_CHARS):
        return {
            "status": "error",
            "message": f"Email body is unusually long (over {MAX_BODY_CHARS} chars) - summarize before sending.",
        }

    if body_html:
        message = MIMEMultipart("alternative")
        message["From"] = SENDER_EMAIL
        message["To"] = recipient_email
        message["Subject"] = subject

        plain_part = _create_utf8_text(body, "plain")
        message.attach(plain_part)

        if inline_images:
            related_part = MIMEMultipart("related")
            html_part = _create_utf8_text(body_html, "html")
            related_part.attach(html_part)

            for img in inline_images:
                img_part = MIMEImage(img["bytes"], _subtype=img.get("subtype", "png"))
                img_part.add_header("Content-ID", f"<{img['cid']}>")
                img_part.add_header(
                    "Content-Disposition",
                    "inline",
                    filename=img.get("filename", f"{img['cid']}.png")
                )
                related_part.attach(img_part)

            message.attach(related_part)
        else:
            html_part = _create_utf8_text(body_html, "html")
            message.attach(html_part)
    else:
        message = MIMEMultipart()
        message["From"] = SENDER_EMAIL
        message["To"] = recipient_email
        message["Subject"] = subject
        plain_part = _create_utf8_text(body, "plain")
        message.attach(plain_part)

    try:
        context = ssl.create_default_context(cafile=certifi.where())
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls(context=context)
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, message.as_string())
    except smtplib.SMTPAuthenticationError:
        return {
            "status": "error",
            "message": (
                "SMTP authentication failed. Check SMTP_EMAIL and SMTP_PASSWORD in "
                ".env, and confirm the Google App Password is valid."
            ),
        }
    except smtplib.SMTPRecipientsRefused:
        return {"status": "error", "message": f"'{recipient_email}' was refused by the mail server."}
    except (smtplib.SMTPException, OSError) as e:
        return {"status": "error", "message": f"Failed to send email: {e}"}

    sent_at = datetime.now(timezone.utc).isoformat()
    print(f"[EMAIL SENT] to={recipient_email} subject='{subject}' at={sent_at}")

    return {
        "status": "success",
        "message": f"Email sent to {recipient_email}.",
        "recipient": recipient_email,
        "subject": subject,
        "sent_at": sent_at,
    }


if __name__ == "__main__":
    result = send_email_smtp(
        recipient_email="test@example.com",
        subject="Test email",
        body="This is a test email from the logistics assistant.",
    )
    print(result)