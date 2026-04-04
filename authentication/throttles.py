from rest_framework.throttling import AnonRateThrottle

class OTPVerifyThrottle(AnonRateThrottle):
  """Limit OTP verification to 5 attempts per hour per IP."""
  scope = "otp_verify"

class LoginThrottle(AnonRateThrottle):
  """Limit login attempts to 10 per hour per IP."""
  scope = "login"