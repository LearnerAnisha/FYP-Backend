"""
serializers.py
---------------
Defines serializers for user registration and login validation.
"""

from rest_framework import serializers
from .models import User

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """

    password = serializers.CharField(write_only=True)
    accepted_terms = serializers.BooleanField(required=True)

    class Meta:
        model = User
        fields = ["full_name", "email", "phone", "password", "accepted_terms"]

    def validate_accepted_terms(self, value):
        """
        Ensures the user accepts the system's terms and conditions.
        """
        if not value:
            raise serializers.ValidationError(
                "You must accept the Terms and Conditions."
            )
        return value

    def create(self, validated_data):
        """
        Creates a new user using the custom UserManager.
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
            raise serializers.ValidationError("User not found")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid password")

        data["user"] = user
        return data
