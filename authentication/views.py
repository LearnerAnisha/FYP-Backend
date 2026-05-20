"""
views.py
---------
Defines API endpoints for:
1. User registration
2. Email OTP verification
3. JWT-based authentication
4. Forgot / Reset Password
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, EmailOTP, generate_otp, SavedReport
from .serializers import ProfileSerializer, RegisterSerializer, LoginSerializer
from .email import send_otp_email, send_password_reset_email
from django.contrib.auth.password_validation import validate_password
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveUpdateAPIView
from django.utils import timezone
import secrets
import hashlib
from datetime import timedelta

# In-memory token store: token_hash -> {user_id, expires_at}
# For multi-server / production, replace with a DB model or Redis.
_reset_tokens = {}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return Response(
                {"status": "error", "errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = serializer.save(is_verified=False)
        otp_code = generate_otp()
        EmailOTP.objects.update_or_create(user=user, defaults={"code": otp_code})
        try:
            send_otp_email(user, otp_code)
        except Exception:
            return Response(
                {
                    "status": "success",
                    "message": "Account created but email delivery failed. Use resend OTP.",
                    "email": user.email,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "status": "success",
                "message": "Registration successful. OTP sent to your email.",
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp_input = request.data.get("otp")
        try:
            user = User.objects.get(email=email)
            otp_obj = EmailOTP.objects.get(user=user)
        except (User.DoesNotExist, EmailOTP.DoesNotExist):
            return Response(
                {"message": "Invalid email or OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if otp_obj.is_expired():
            otp_obj.delete()
            return Response(
                {"message": "OTP has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if otp_obj.code != otp_input:
            return Response(
                {"message": "Incorrect OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_verified = True
        user.save()
        otp_obj.delete()
        return Response(
            {"message": "Email verified successfully."},
            status=status.HTTP_200_OK,
        )


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if not user.is_verified:
            return Response(
                {"message": "Email verification required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                },
            },
            status=status.HTTP_200_OK,
        )


#  Forgot Password
class ForgotPasswordView(APIView):
    """
    POST /api/auth/forgot-password/
    Body: { "email": "user@example.com" }

    Sends a password-reset link to the given email.
    Always returns 200 to prevent email enumeration.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()

        if not email:
            return Response(
                {"message": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        GENERIC_MSG = "If an account exists for this email, a reset link has been sent."

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"message": GENERIC_MSG}, status=status.HTTP_200_OK)

        # Generate a secure URL-safe token
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = timezone.now() + timedelta(minutes=30)

        _reset_tokens[token_hash] = {
            "user_id": user.id,
            "expires_at": expires_at,
        }

        from django.conf import settings as django_settings

        frontend_url = getattr(django_settings, "FRONTEND_URL", "http://localhost:5173")
        reset_link = f"{frontend_url}/reset-password?token={raw_token}"

        try:
            send_password_reset_email(user, reset_link)
        except Exception:
            return Response(
                {"message": "Failed to send reset email. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"message": GENERIC_MSG}, status=status.HTTP_200_OK)


#  Reset Password
class ResetPasswordView(APIView):
    """
    POST /api/auth/reset-password/
    Body: { "token": "<from_email_link>", "password": "newPass123!" }

    Validates the token, sets the new password, then invalidates the token.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        raw_token = request.data.get("token", "").strip()
        new_password = request.data.get("password", "").strip()

        if not raw_token or not new_password:
            return Response(
                {"message": "Token and new password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_hash = _hash_token(raw_token)
        entry = _reset_tokens.get(token_hash)

        if not entry:
            return Response(
                {"message": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if timezone.now() > entry["expires_at"]:
            del _reset_tokens[token_hash]
            return Response(
                {"message": "Reset link has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=entry["user_id"])
        except User.DoesNotExist:
            del _reset_tokens[token_hash]
            return Response(
                {"message": "User not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response(
                {"message": e.messages[0] if e.messages else "Password is too weak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        del _reset_tokens[token_hash]  # One-time use

        return Response(
            {"message": "Password reset successfully. You can now log in."},
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────
#  Existing views (unchanged below)
# ─────────────────────────────────────────────
class ProfileView(RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get("current")
        new_password = request.data.get("new")

        if not user.check_password(current_password):
            return Response({"message": "Current password is incorrect."}, status=400)

        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response({"errors": e.messages}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({"message": "Password updated successfully."}, status=200)


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        subscription = getattr(user, "subscription", None)
        if not (subscription and subscription.is_pro):
            return Response(
                {"message": "Account deletion is available for PRO subscribers only."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.delete()
        return Response({"message": "Account deleted successfully"}, status=204)


class ExportDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        subscription = getattr(user, "subscription", None)
        if not (subscription and subscription.is_pro):
            return Response(
                {"message": "Data export is available for PRO subscribers only."},
                status=status.HTTP_403_FORBIDDEN,
            )

        farmer_profile = getattr(user, "farmer_profile", None)
        account_data = {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone or "",
            "date_joined": user.date_joined.isoformat() if user.date_joined else None,
            "is_verified": user.is_verified,
            "farmer_profile": (
                {
                    "farm_size": (
                        str(farmer_profile.farm_size)
                        if farmer_profile and farmer_profile.farm_size
                        else None
                    ),
                    "experience": farmer_profile.experience if farmer_profile else None,
                    "crop_types": farmer_profile.crop_types if farmer_profile else None,
                    "language": farmer_profile.language if farmer_profile else None,
                    "bio": farmer_profile.bio if farmer_profile else None,
                }
                if farmer_profile
                else None
            ),
            "subscription": {
                "plan": subscription.plan,
                "is_active": subscription.is_active,
                "starts_at": (
                    subscription.starts_at.isoformat()
                    if subscription.starts_at
                    else None
                ),
                "expires_at": (
                    subscription.expires_at.isoformat()
                    if subscription.expires_at
                    else None
                ),
            },
        }

        from CropDiseaseDetection.models import ScanResult

        scans = ScanResult.objects.filter(user=user).order_by("-created_at")
        scans_data = [
            {
                "id": s.id,
                "crop_type": s.crop_type,
                "disease": s.disease,
                "confidence": round(s.confidence, 2),
                "is_healthy": s.is_healthy,
                "severity": s.severity,
                "description": s.description,
                "treatment": s.treatment,
                "prevention": s.prevention,
                "scanned_at": s.created_at.isoformat(),
            }
            for s in scans
        ]

        from chatbot.models import ChatConversation

        conversations = (
            ChatConversation.objects.filter(user=user)
            .prefetch_related("messages")
            .order_by("-created_at")
        )
        chats_data = [
            {
                "session_id": conv.session_id,
                "started_at": conv.created_at.isoformat(),
                "last_active": conv.updated_at.isoformat(),
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                    }
                    for msg in conv.messages.all()
                ],
            }
            for conv in conversations
        ]

        from chatbot.models import CropSuggestion

        suggestions = CropSuggestion.objects.filter(conversation__user=user).order_by(
            "-created_at"
        )
        suggestions_data = [
            {
                "id": s.id,
                "crop_name": s.crop_name,
                "growth_stage": s.growth_stage,
                "weather_conditions": s.weather_conditions,
                "suggestion": s.suggestion,
                "suggested_at": s.created_at.isoformat(),
            }
            for s in suggestions
        ]

        export_payload = {
            "exported_at": timezone.now().isoformat(),
            "account": account_data,
            "disease_scans": {"total": len(scans_data), "records": scans_data},
            "chatbot_conversations": {"total": len(chats_data), "records": chats_data},
            "crop_suggestions": {
                "total": len(suggestions_data),
                "records": suggestions_data,
            },
        }

        SavedReport.objects.create(user=user, report_data=export_payload)

        from django.http import JsonResponse

        response = JsonResponse(export_payload, json_dumps_params={"indent": 2})
        response["Content-Disposition"] = (
            'attachment; filename="krishisathi_export.json"'
        )
        return response


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"message": "Email is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"message": "No account found with this email."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if user.is_verified:
            return Response(
                {"message": "This account is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        otp_code = generate_otp()
        EmailOTP.objects.update_or_create(user=user, defaults={"code": otp_code})
        try:
            send_otp_email(user, otp_code)
        except Exception:
            return Response(
                {"message": "Failed to send email. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {"message": "A new OTP has been sent to your email."},
            status=status.HTTP_200_OK,
        )
