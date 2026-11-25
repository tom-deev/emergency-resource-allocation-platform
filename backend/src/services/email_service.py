"""
Gmail SMTP Email Delivery Service for Resource Operator OTP Authentication.

Uses Python's built-in smtplib, ssl (STARTTLS with certificate verification),
and email.message.EmailMessage. Never logs or exposes SMTP passwords or OTPs.
"""

from email.message import EmailMessage
import logging
import os
import smtplib
import ssl


logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when OTP email configuration is missing or SMTP delivery fails."""


def send_operator_otp_email(
    username: str,
    otp_code: str,
    ttl_seconds: int = 300,
    smtp_factory=smtplib.SMTP,
) -> None:
    """
    Send a 6-digit login OTP email to the configured operator recipient via
    Gmail SMTP (STARTTLS with TLS certificate verification).
    """
    smtp_host = (os.environ.get("SMTP_HOST") or "smtp.gmail.com").strip()
    raw_port = (os.environ.get("SMTP_PORT") or "587").strip()
    smtp_username = (os.environ.get("SMTP_USERNAME") or "").strip()
    smtp_password = (os.environ.get("SMTP_PASSWORD") or "").strip()
    email_from = (os.environ.get("OTP_EMAIL_FROM") or smtp_username).strip()
    email_to = (os.environ.get("OTP_EMAIL_TO") or smtp_username).strip()

    try:
        smtp_port = int(raw_port)
    except ValueError as exc:
        raise EmailDeliveryError("Invalid SMTP_PORT configuration.") from exc

    if (
        not smtp_host
        or not smtp_username
        or not smtp_password
        or not email_from
        or not email_to
        or "replace-with-your" in smtp_password.lower()
    ):
        raise EmailDeliveryError(
            "Gmail SMTP OTP delivery is not configured. "
            "Configure SMTP credentials in backend/.env."
        )

    expiry_minutes = max(1, int(ttl_seconds) // 60)

    message = EmailMessage()
    message["Subject"] = "Emergency Response Platform — Your Login OTP"
    message["From"] = email_from
    message["To"] = email_to
    message.set_content(
        f"Hello {username},\n\n"
        f"Your one-time login verification code (OTP) for the Emergency Response & "
        f"Resource Allocation Platform is:\n\n"
        f"    {otp_code}\n\n"
        f"Security notices:\n"
        f"- This code expires in {expiry_minutes} minutes.\n"
        f"- This code is single-use and becomes invalid after verification or "
        f"if a newer code is requested.\n"
        f"- Do not share this OTP with anyone.\n\n"
        f"If you did not attempt to sign in, you may ignore this email.\n"
    )

    tls_context = ssl.create_default_context()

    try:
        with smtp_factory(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls(context=tls_context)
            server.ehlo()
            server.login(smtp_username, smtp_password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("SMTP OTP delivery failed for operator '%s'.", username)
        raise EmailDeliveryError(
            "Unable to deliver login OTP email. Please try again."
        ) from exc
