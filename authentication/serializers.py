from rest_framework import serializers
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
