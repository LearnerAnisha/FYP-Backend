"""
views.py
---------
Defines API endpoints for:
1. User registration
2. Email OTP verification
3. JWT-based authentication
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, EmailOTP, generate_otp
from .serializers import ProfileSerializer, RegisterSerializer, LoginSerializer
from .email import send_otp_email
from django.contrib.auth.password_validation import validate_password
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveUpdateAPIView
from django.utils import timezone

class RegisterView(generics.CreateAPIView):
    """
    Registers a new user and sends an email OTP for verification.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return Response(
                {
                    "status": "error",
                    "errors": e.detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        user = serializer.save(is_verified=False)
        otp_code = generate_otp()
        EmailOTP.objects.update_or_create(user=user, defaults={"code": otp_code})

        try:
            send_otp_email(user, otp_code)
        except Exception as e:
            # User and OTP are saved — they can resend. Don't 500.
            return Response(
                {
                    "status": "success",
                    "message": "Account created but email delivery failed. Use resend OTP.",
                    "email": user.email,
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                "status": "success",
                "message": "Registration successful. OTP sent to your email.",
                "email": user.email,
            },
            status=status.HTTP_201_CREATED
        )

class VerifyOTPView(APIView):
    """
    Verifies the OTP submitted by the user.
    """

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
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.is_expired():
            otp_obj.delete()
            return Response(
                {"message": "OTP has expired."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.code != otp_input:
            return Response(
                {"message": "Incorrect OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_verified = True
        user.save()
        otp_obj.delete()

        return Response(
            {"message": "Email verified successfully."},
            status=status.HTTP_200_OK
        )

class LoginView(generics.GenericAPIView):
    """
    Authenticates verified users and issues JWT tokens.
    """

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        if not user.is_verified:
            return Response(
                {"message": "Email verification required."},
                status=status.HTTP_403_FORBIDDEN
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
                    "phone": user.phone
                }
            },
            status=status.HTTP_200_OK
        )
class ProfileView(RetrieveUpdateAPIView):
    """
    API endpoint for retrieving and updating
    the currently authenticated user's profile.

    HTTP Methods:
    - GET  : Retrieve profile data
    - PUT  : Update profile data

    Security:
    - Requires valid JWT token
    - Users can only access their own profile
    """

    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Returns the currently authenticated user.

        DRF automatically sets request.user
        when a valid JWT token is provided.
        """
        return self.request.user
class ChangePasswordView(APIView):
    """
    API endpoint for changing user password.

    Workflow:
    1. Verify current password
    2. Validate new password against Django's password policies
    3. Save the new password securely

    Security:
    - JWT authentication required
    - Old password must be correct
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles password change request.
        """

        user = request.user
        current_password = request.data.get("current")
        new_password = request.data.get("new")

        # Step 1: Validate current password
        if not user.check_password(current_password):
            return Response(
                {"message": "Current password is incorrect."},
                status=400
            )

        # Step 2: Validate new password strength
        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response(
                {"errors": e.messages},
                status=400
            )

        # Step 3: Set and save new password
        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Password updated successfully."},
            status=200
        )


# Delete account — PRO subscribers only
class DeleteAccountView(APIView):
    """
    Permanently deletes the authenticated user's account.
    Restricted to PRO subscribers only.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user

        # Guard: only PRO users can delete
        subscription = getattr(user, "subscription", None)
        if not (subscription and subscription.is_pro):
            return Response(
                {
                    "message": "Account deletion is available for PRO subscribers only. "
                    "Please upgrade your plan to access this feature."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        user.delete()
        return Response({"message": "Account deleted successfully"}, status=204)


# Export data — PRO subscribers only
class ExportDataView(APIView):
    """
    Returns a downloadable JSON export of the authenticated user's full data.
    Includes: account info, crop disease scans, chatbot conversations, crop suggestions.
    Restricted to PRO subscribers only.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # PRO guard
        subscription = getattr(user, "subscription", None)
        if not (subscription and subscription.is_pro):
            return Response(
                {
                    "message": "Data export is available for PRO subscribers only. "
                    "Please upgrade your plan to access this feature."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Account
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

        # Crop Disease Scans
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

        # Chatbot Conversations
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

        # Crop Suggestions
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

        # Final Payload
        export_payload = {
            "exported_at": timezone.now().isoformat(),
            "account": account_data,
            "disease_scans": {
                "total": len(scans_data),
                "records": scans_data,
            },
            "chatbot_conversations": {
                "total": len(chats_data),
                "records": chats_data,
            },
            "crop_suggestions": {
                "total": len(suggestions_data),
                "records": suggestions_data,
            },
        }

        from django.http import JsonResponse

        response = JsonResponse(export_payload, json_dumps_params={"indent": 2})
        response["Content-Disposition"] = (
            'attachment; filename="krishisathi_export.json"'
        )
        return response


# Resend OTP
class ResendOTPView(APIView):
    """
    Resends a fresh OTP to the user's email.
    Only works for unverified accounts.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response(
                {"message": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"message": "No account found with this email."},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.is_verified:
            return Response(
                {"message": "This account is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp_code = generate_otp()
        EmailOTP.objects.update_or_create(
            user=user,
            defaults={"code": otp_code}
        )

        try:
            send_otp_email(user, otp_code)
        except Exception:
            return Response(
                {"message": "Failed to send email. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"message": "A new OTP has been sent to your email."},
            status=status.HTTP_200_OK
        )
