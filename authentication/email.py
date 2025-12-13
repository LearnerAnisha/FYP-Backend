"""
email.py
---------
Handles email delivery using Azure Communication Services (ACS).
"""

from azure.communication.email import EmailClient
from django.conf import settings

def send_otp_email(user, otp_code):
    """
    Sends an OTP email using Azure Communication Services.

    Parameters:
        user (User): Target user
        otp_code (str): Generated OTP
    """

    client = EmailClient.from_connection_string(
        settings.AZURE_EMAIL_CONNECTION_STRING
    )

    message = {
        "senderAddress": settings.AZURE_SENDER_EMAIL,
        "recipients": {
            "to": [{"address": user.email}]
        },
        "content": {
            "subject": "Email Verification OTP",
            "plainText": f"Your OTP is {otp_code}. It expires in 10 minutes.",
            "html": (
                "<p>Your OTP is <strong>"
                f"{otp_code}</strong>. It expires in 10 minutes.</p>"
            )
        }
    }

    client.begin_send(message)
