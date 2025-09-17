"""Utilities for sending transactional emails."""

from __future__ import annotations

from email.message import EmailMessage
import smtplib

from app.core.config import settings


class EmailDeliveryError(Exception):
    """Raised when an email could not be delivered."""


def build_confirmation_email(recipient: str, confirmation_link: str) -> EmailMessage:
    """Construct the confirmation email message."""

    message = EmailMessage()
    message["Subject"] = "Confirm your Action-Reaction account"
    message["From"] = settings.email_sender
    message["To"] = recipient
    message.set_content(
        (
            "Thanks for signing up for Action-Reaction!\n\n"
            "Please confirm your email address by clicking the link below:\n"
            f"{confirmation_link}\n\n"
            "If you did not create this account, you can ignore this email."
        )
    )
    message.add_alternative(
        (
            "<p>Thanks for signing up for Action-Reaction!</p>"
            "<p>Please confirm your email address by clicking the button below.</p>"
            f"<p><a href=\"{confirmation_link}\">Confirm my email</a></p>"
            "<p>If you did not create this account, you can ignore this email.</p>"
        ),
        subtype="html",
    )
    return message


def send_email(message: EmailMessage) -> None:
    """Send an email using the configured SMTP server."""

    host = settings.smtp_host
    port = settings.smtp_port
    username = settings.smtp_username or None
    password = settings.smtp_password or None
    use_tls = settings.smtp_use_tls

    try:
        with smtplib.SMTP(host=host, port=port) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
    except smtplib.SMTPException as exc:  # pragma: no cover - network failure path
        raise EmailDeliveryError("Failed to send email") from exc


def send_confirmation_email(recipient: str, confirmation_link: str) -> None:
    """High-level helper for dispatching confirmation emails."""

    message = build_confirmation_email(recipient, confirmation_link)
    send_email(message)


__all__ = [
    "EmailDeliveryError",
    "build_confirmation_email",
    "send_confirmation_email",
    "send_email",
]

