from rest_framework import serializers
from .models import ChatConversation, ChatMessage, CropSuggestion

class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages"""
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'timestamp']
        read_only_fields = ['id', 'timestamp']

class ChatConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations with all messages"""
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatConversation
        fields = ['id', 'session_id', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['id', 'created_at', 'updated_at']

class WeatherRequestSerializer(serializers.Serializer):
    """Input validation for weather requests"""
    location = serializers.CharField(max_length=255)

class CropSuggestionRequestSerializer(serializers.Serializer):
    """Input validation for crop suggestion requests"""
    location = serializers.CharField(max_length=255)
    crop_name = serializers.CharField(max_length=100)
    growth_stage = serializers.CharField(max_length=100)
    session_id = serializers.CharField(max_length=255, required=False)

class CropSuggestionSerializer(serializers.ModelSerializer):
    """Serializer for crop suggestions"""
    class Meta:
        model = CropSuggestion
        fields = ['id', 'crop_name', 'growth_stage', 'weather_conditions', 'suggestion', 'created_at']
        read_only_fields = ['id', 'created_at']

class ChatRequestSerializer(serializers.Serializer):
    """Input validation for general chat requests"""
    session_id = serializers.CharField(max_length=255)
    message = serializers.CharField()

class ChatResponseSerializer(serializers.Serializer):
    """Response format for chat"""
    session_id = serializers.CharField()
    response = serializers.CharField()
    timestamp = serializers.DateTimeField()