from django.urls import path
from .views import (
    UserConversationsView,
    WeatherView,
    CropSuggestionView,
    ChatView,
    ConversationHistoryView,
    DeleteConversationView,
    EditMessageView
)

urlpatterns = [
    # Weather endpoint
    path('weather/', WeatherView.as_view(), name='weather'),
    
    # Crop suggestion endpoint (your main feature!)
    path('crop-suggestion/', CropSuggestionView.as_view(), name='crop-suggestion'),
    
    # General chat endpoint
    path('chat/', ChatView.as_view(), name='chat'),
    
    # Conversation history
    path('conversation/<str:session_id>/', ConversationHistoryView.as_view(), name='conversation-history'),
    
    # all conversations
    path('conversations/', UserConversationsView.as_view(), name='user-conversations'),
    
    path('conversation/<str:session_id>/delete/', DeleteConversationView.as_view()),
    path('message/<int:message_id>/edit/', EditMessageView.as_view()),
]