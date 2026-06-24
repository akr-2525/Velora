"""
Velora email sending — uses Resend API (HTTP, not SMTP).
Render free tier blocks outbound SMTP ports, so we use Resend's HTTP API instead.
Free tier: 3,000 emails/month — plenty for Velora.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SENDER_EMAIL   = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")
SENDER_NAME    = os.getenv("SENDER_NAME", "Velora")


def send_email(to_email: str, subject: str, html_content: str) -> None:
    """
    Send a single HTML email via Resend HTTP API.
    No SMTP ports needed — works on Render free tier.
    """
    if not RESEND_API_KEY:
        raise RuntimeError(
            "RESEND_API_KEY environment variable is not set. "
            "Sign up at resend.com and add the key to Render env vars."
        )

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from":    f"{SENDER_NAME} <{SENDER_EMAIL}>",
            "to":      [to_email],
            "subject": subject,
            "html":    html_content,
        },
        timeout=15,
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Resend API error {response.status_code}: {response.text}"
        )
