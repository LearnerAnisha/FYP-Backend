from django.db import models
from authentication.models import User

class ChatConversation(models.Model):
    """Stores each conversation session"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Conversation {self.session_id}"

class ChatMessage(models.Model):
    """Stores individual messages in a conversation"""
    conversation = models.ForeignKey(ChatConversation, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}"

class WeatherData(models.Model):
    """Caches weather data to reduce API calls"""
    location = models.CharField(max_length=255)
    current_weather = models.JSONField()
    forecast_data = models.JSONField()
    fetched_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Weather for {self.location}"

class CropSuggestion(models.Model):
    """Stores crop suggestions for reference"""
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE)
    crop_name = models.CharField(max_length=100)
    growth_stage = models.CharField(max_length=100)
    weather_conditions = models.JSONField()
    suggestion = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.crop_name} - {self.growth_stage}"