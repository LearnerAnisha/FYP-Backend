"""
serializers.py
---------------
Defines serializers for user registration and login validation
with strong input validation and clear error messages.
"""

import re
from rest_framework import serializers
from .models import User
from django.utils.timezone import now

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with strong validation rules.
    """

    password = serializers.CharField(write_only=True)
    accepted_terms = serializers.BooleanField(required=True)

    class Meta:
        model = User
        fields = ["full_name", "email", "phone", "password", "accepted_terms"]

    def validate_full_name(self, value):
        """
        Full name validation:
        - At least two words
        - Only letters and spaces
        """
        value = value.strip()

        if len(value.split()) < 2:
            raise serializers.ValidationError(
                "Full name must include at least first and last name."
            )

        if not re.match(r"^[A-Za-z ]+$", value):
            raise serializers.ValidationError(
                "Full name can only contain letters and spaces."
            )

        return value

    def validate_phone(self, value):
        """
        Nepal phone number validation:
        - Must start with 98 or 97
        - Must be exactly 10 digits
        """
        if not re.match(r"^(98|97)\d{8}$", value):
            raise serializers.ValidationError(
                "Phone number must start with 98 or 97 and contain exactly 10 digits."
            )
        return value

    def validate_password(self, value):
        """
        Strong password policy:
        - Minimum 8 characters
        - At least 1 uppercase letter
        - At least 1 number
        - At least 1 special character
        """
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long."
            )

        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter."
            )

        if not re.search(r"[0-9]", value):
            raise serializers.ValidationError(
                "Password must contain at least one number."
            )

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise serializers.ValidationError(
                "Password must contain at least one special character."
            )

        return value

    def validate(self, data):
        """
        Prevent duplicate email and phone numbers.
        """
        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError(
                {"email": "An account with this email already exists."}
            )

        if User.objects.filter(phone=data["phone"]).exists():
            raise serializers.ValidationError(
                {"phone": "An account with this phone number already exists."}
            )

        return data

    def create(self, validated_data):
        """
        Create user using custom UserManager.
        """
        return User.objects.create_user(**validated_data)

class LoginSerializer(serializers.Serializer):
    """
    Serializer for login using email or phone number.
    """

    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get("identifier")
        password = data.get("password")

        user = (
            User.objects.filter(email=identifier).first()
            or User.objects.filter(phone=identifier).first()
        )

        if not user:
            raise serializers.ValidationError("User not found.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid password.")

        data["user"] = user
        return data
class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving and updating user profile data.
    """
    active_days = serializers.SerializerMethodField() 
    class Meta:
        model = User
        # Fields that will be exposed to frontend
        fields = [
            "full_name",
            "email",
            "phone",
            "avatar",
            "date_joined",
            "active_days",
        ]
        # Email should never be editable once registered
        read_only_fields = ["email", "date_joined"]

    def get_active_days(self, obj):
        return (now().date() - obj.date_joined.date()).days + 1
    
    def validate_avatar(self, value):
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Image size must be under 2MB.")

        if not value.content_type.startswith("image/"):
            raise serializers.ValidationError("Only image files are allowed.")

        return value