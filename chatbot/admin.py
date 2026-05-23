from django.contrib import admin
from .models import ChatConversation, ChatMessage, WeatherData, CropSuggestion

@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    """Admin interface for conversations"""
    list_display = ['session_id', 'user', 'is_deleted', 'created_at', 'updated_at', 'deleted_at']
    list_filter = ['is_deleted', 'created_at']
    search_fields = ['session_id', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin interface for messages"""
    list_display = ['conversation', 'role', 'content_preview', 'is_edited', 'timestamp']
    list_filter = ['role', 'is_edited', 'timestamp']
    search_fields = ['content', 'original_content', 'conversation__session_id']
    readonly_fields = ['timestamp', 'original_content', 'edited_at']
    readonly_fields = ['timestamp']
    
    def content_preview(self, obj):
        """Show first 50 characters of content"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'

@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    """Admin interface for weather cache"""
    list_display = ['location', 'fetched_at']
    list_filter = ['fetched_at']
    search_fields = ['location']
    readonly_fields = ['fetched_at']

@admin.register(CropSuggestion)
class CropSuggestionAdmin(admin.ModelAdmin):
    """Admin interface for crop suggestions"""
    list_display = ['crop_name', 'growth_stage', 'conversation', 'created_at']
    list_filter = ['crop_name', 'growth_stage', 'created_at']
    search_fields = ['crop_name', 'growth_stage', 'suggestion']
    readonly_fields = ['created_at']