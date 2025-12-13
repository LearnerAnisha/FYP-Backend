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
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, EmailOTP, generate_otp
from .serializers import RegisterSerializer, LoginSerializer
from .email import send_otp_email

class RegisterView(generics.CreateAPIView):
    """
    Registers a new user and sends an email OTP for verification.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save(is_verified=False)

        otp_code = generate_otp()
        EmailOTP.objects.update_or_create(
            user=user,
            defaults={"code": otp_code}
        )

        send_otp_email(user, otp_code)

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            {"message": "Registration successful. OTP sent to your email."},
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
                {"message": "Invalid email or OTP"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.is_expired():
            otp_obj.delete()
            return Response(
                {"message": "OTP has expired"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.code != otp_input:
            return Response(
                {"message": "Incorrect OTP"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_verified = True
        user.save()
        otp_obj.delete()

        return Response(
            {"message": "Email verified successfully"},
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
                {"message": "Email verification required"},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone
            }
        })
