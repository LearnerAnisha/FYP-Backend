import requests
from django.conf import settings

SPARROW_SMS_URL = "http://api.sparrowsms.com/v2/sms/"


def send_otp_sms(user, otp_code):
    phone = getattr(user, "phone", None)
    if not phone:
        raise ValueError(f"User {user.email} has no phone number registered.")

    payload = {
        "token": settings.SPARROW_SMS_TOKEN,
        "from": settings.SPARROW_SMS_FROM,
        "to": phone,
        "text": f"Your KrishiSathi OTP is: {otp_code}. Valid for 10 minutes. Do not share it.",
    }
    response = requests.post(SPARROW_SMS_URL, data=payload, timeout=10)
    response.raise_for_status()
    return response.json()
