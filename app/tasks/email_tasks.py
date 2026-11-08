"""Email tasks for Celery."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.tasks.celery_app import celery_app
from app.core.config import settings


@celery_app.task
def send_activation_email(email: str, token: str):
    """Send activation email to user."""
    subject = "Activate your Online Cinema account"
    activation_link = f"{settings.frontend_url.rstrip('/')}/activate?token={token}"

    body = f"""
    Hello!

    Please activate your account by clicking the link below:
    {activation_link}

    This link will expire in 24 hours.

    Best regards,
    Online Cinema Team
    """

    _send_email(email, subject, body)


@celery_app.task
def send_password_reset_email(email: str, token: str):
    """Send password reset email to user."""
    subject = "Reset your Online Cinema password"
    reset_link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"

    body = f"""
    Hello!

    You requested a password reset. Click the link below to reset your password:
    {reset_link}

    This link will expire in 1 hour.

    If you didn't request this, please ignore this email.

    Best regards,
    Online Cinema Team
    """

    _send_email(email, subject, body)


def _send_email(to_email: str, subject: str, body: str):
    """Send email using SMTP."""
    msg = MIMEMultipart()
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")
