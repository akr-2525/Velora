import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

def send_email(to_email: str, subject: str, html_content: str):
    # Put your actual Gmail address and App Password here!
    SENDER_EMAIL = os.getenv("SENDER_EMAIL") 
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
    
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    
    # We tell Gmail this is an HTML file, not plain text
    msg.set_content(html_content, subtype='html')

    try:
        # Connect to Gmail's secure server
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        # This will pass the real error back to our scheduler
        raise Exception(f"Gmail failed to send: {e}")