from rest_framework import serializers
from .models import ChatConversation, ChatMessage, CropSuggestion

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "timestamp"]
        read_only_fields = ["id", "timestamp"]

class ConversationUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

class ChatConversationSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    user = ConversationUserSerializer(read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = [
            "id",
            "session_id",
            "user",
            "created_at",
            "updated_at",
            "messages",
            "message_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.messages.count()


class WeatherRequestSerializer(serializers.Serializer):
    location = serializers.CharField(max_length=255)

class CropSuggestionRequestSerializer(serializers.Serializer):
    location = serializers.CharField(max_length=255)
    crop_name = serializers.CharField(max_length=100)
    growth_stage = serializers.CharField(max_length=100)
    session_id = serializers.CharField(max_length=255, required=False)

class CropSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropSuggestion
        fields = [
            "id",
            "crop_name",
            "growth_stage",
            "weather_conditions",
            "suggestion",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ChatRequestSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255)
    message = serializers.CharField()

class ChatResponseSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    response = serializers.CharField()
    timestamp = serializers.DateTimeField()