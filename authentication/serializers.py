from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    accepted_terms = serializers.BooleanField(required=True)

    class Meta:
        model = User
        fields = ["full_name", "email", "phone", "password", "accepted_terms"]

    def validate_accepted_terms(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the Terms & Privacy Policy")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()  # email or phone
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get("identifier")
        password = data.get("password")

        # Find user by email OR phone
        user = User.objects.filter(email=identifier).first() or \
               User.objects.filter(phone=identifier).first()

        if not user:
            raise serializers.ValidationError("User not found")

        if not user.check_password(password):
            raise serializers.ValidationError("Incorrect password")

        data["user"] = user
        return data
