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
        EmailOTP.objects.update_or_create(
            user=user,
            defaults={"code": otp_code}
        )

        send_otp_email(user, otp_code)

        return Response(
            {
                "status": "success",
                "message": "Registration successful. OTP sent to your email."
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