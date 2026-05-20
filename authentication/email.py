"""
email.py
---------
Handles email delivery using Azure Communication Services (ACS).
"""

from azure.communication.email import EmailClient
from django.conf import settings


def send_otp_email(user, otp_code):
    client = EmailClient.from_connection_string(settings.AZURE_EMAIL_CONNECTION_STRING)
    message = {
        "senderAddress": settings.AZURE_SENDER_EMAIL,
        "recipients": {"to": [{"address": user.email}]},
        "content": {
            "subject": "Email Verification OTP",
            "plainText": f"Your OTP is {otp_code}. It expires in 10 minutes.",
            "html": (
                "<p>Your OTP is <strong>"
                f"{otp_code}</strong>. It expires in 10 minutes.</p>"
            ),
        },
    }
    client.begin_send(message)


def send_password_reset_email(user, reset_link):
    """
    Sends a password-reset link email via Azure Communication Services.
    """
    client = EmailClient.from_connection_string(settings.AZURE_EMAIL_CONNECTION_STRING)
    message = {
        "senderAddress": settings.AZURE_SENDER_EMAIL,
        "recipients": {"to": [{"address": user.email}]},
        "content": {
            "subject": "Reset Your Krishi Saathi Password",
            "plainText": (
                f"Hello {user.full_name},\n\n"
                "We received a request to reset your password.\n"
                f"Click the link below (valid for 30 minutes):\n\n"
                f"{reset_link}\n\n"
                "If you did not request this, please ignore this email."
            ),
            "html": (
                f"<p>Hello <strong>{user.full_name}</strong>,</p>"
                "<p>We received a request to reset your password.</p>"
                "<p>This link is valid for <strong>30 minutes</strong>.</p>"
                f'<p><a href="{reset_link}" style="background:#16a34a;color:#fff;'
                "padding:10px 24px;border-radius:6px;text-decoration:none;"
                'display:inline-block;font-weight:600;">Reset Password</a></p>'
                "<p>If you did not request this, please ignore this email.</p>"
            ),
        },
    }
    client.begin_send(message)
