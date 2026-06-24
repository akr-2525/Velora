"""
Velora email sending — uses Brevo (Sendinblue) HTTP API.
300 free emails/day, no domain ownership required, works on Render free tier.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL  = os.getenv("SENDER_EMAIL", "hello@velora.app")
SENDER_NAME   = os.getenv("SENDER_NAME",  "Velora")


def send_email(to_email: str, subject: str, html_content: str) -> None:
    """
    Send a single HTML email via Brevo HTTP API.
    No SMTP ports needed — works on Render free tier.
    300 free emails/day on Brevo free plan.
    """
    if not BREVO_API_KEY:
        raise RuntimeError(
            "BREVO_API_KEY environment variable is not set. "
            "Sign up at brevo.com and add the API key to Render env vars."
        )

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key":      BREVO_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "sender":      {"name": SENDER_NAME, "email": SENDER_EMAIL},
            "to":          [{"email": to_email}],
            "subject":     subject,
            "htmlContent": html_content,
        },
        timeout=15,
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Brevo API error {response.status_code}: {response.text}"
        )
