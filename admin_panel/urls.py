"""
admin_panel/urls.py
-------------------
URL configuration for admin panel.
"""

from django.urls import path
from .views import (
    # Authentication & Dashboard
    AdminLoginView,
    AdminDashboardStatsView,
    
    # User Management
    AdminUserListView,
    AdminUserDetailView,
    AdminToggleUserStatusView,
    AdminVerifyUserView,
    
    # Activity Logs
    AdminActivityLogListView,
    
    # Chatbot
    ChatConversationListView,
    ChatConversationDetailView,
    ChatMessageListView,
    CropSuggestionListView,
    WeatherDataListView,
    
    # Crop Disease Detection
    ScanResultListView,
    ScanResultDetailView,
    
    # price predictor
    AdminMasterProductListView,
    AdminDailyPriceHistoryListView,
    AdminMarketPriceAnalysisView,
    AdminFetchMarketPricesView,
    AdminPriceStatsView,
)

app_name = 'admin_panel'

urlpatterns = [
    # ========== AUTHENTICATION & DASHBOARD ==========
    path('login/', AdminLoginView.as_view(), name='admin-login'),
    path('dashboard/stats/', AdminDashboardStatsView.as_view(), name='dashboard-stats'),
    
    # ========== USER MANAGEMENT ==========
    path('users/', AdminUserListView.as_view(), name='users-list'),
    path('users/<int:id>/', AdminUserDetailView.as_view(), name='user-detail'),
    path('users/<int:id>/toggle-status/', AdminToggleUserStatusView.as_view(), name='toggle-status'),
    path('users/<int:id>/verify/', AdminVerifyUserView.as_view(), name='verify-user'),
    
    # ========== ACTIVITY LOGS ==========
    path('activity-logs/', AdminActivityLogListView.as_view(), name='activity-logs'),
    
    # ========== CHATBOT ==========
    path('chat-conversations/', ChatConversationListView.as_view(), name='chat-conversations'),
    path('chat-conversations/<int:pk>/', ChatConversationDetailView.as_view(), name='chat-conversation-detail'),
    path('chat-messages/', ChatMessageListView.as_view(), name='chat-messages'),
    path('crop-suggestions/', CropSuggestionListView.as_view(), name='crop-suggestions'),
    path('weather-data/', WeatherDataListView.as_view(), name='weather-data'),
    
    # ========== CROP DISEASE DETECTION ==========
    path('scan-results/', ScanResultListView.as_view(), name='scan-results'),
    path('scan-results/<int:pk>/', ScanResultDetailView.as_view(), name='scan-result-detail'),
    
    # ========== PRICE PREDICTOR (ADMIN) ==========
    path("products/", AdminMasterProductListView.as_view(), name="admin-products"),
    path("history/", AdminDailyPriceHistoryListView.as_view(), name="admin-price-history"),
    path("analysis/", AdminMarketPriceAnalysisView.as_view(), name="admin-price-analysis"),
    path("fetch/", AdminFetchMarketPricesView.as_view(), name="admin-price-fetch"),
    path("price-stats/", AdminPriceStatsView.as_view(), name="admin-price-stats"),
]