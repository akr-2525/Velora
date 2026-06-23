"""
Unified email sending utility for Velora.
Uses Gmail SMTP SSL (port 465) consistently.
All outbound email goes through this single function.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465


def send_email(to_email: str, subject: str, html_content: str) -> None:
    """
    Send a single HTML email via Gmail SMTP SSL.
    Raises on failure so callers can handle or log the error.
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        raise RuntimeError(
            "SENDER_EMAIL or SENDER_PASSWORD env vars are not set."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Velora AI <{SENDER_EMAIL}>"
    msg["To"] = to_email

    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
        smtp.send_message(msg)
