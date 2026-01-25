"""
admin_panel/urls.py
-------------------
URL configuration for admin panel.
"""

from django.urls import path
from .views import (
    AdminLoginView,
    AdminDashboardStatsView,
    AdminUserListView,
    AdminUserDetailView,
    AdminToggleUserStatusView,
    AdminVerifyUserView,
    AdminActivityLogListView,
)

app_name = 'admin_panel'

urlpatterns = [
    # Authentication
    path('login/', AdminLoginView.as_view(), name='admin-login'),
    
    # Dashboard
    path('dashboard/stats/', AdminDashboardStatsView.as_view(), name='dashboard-stats'),
    
    # User Management
    path('users/', AdminUserListView.as_view(), name='users-list'),
    path('users/<int:id>/', AdminUserDetailView.as_view(), name='user-detail'),
    path('users/<int:id>/toggle-status/', AdminToggleUserStatusView.as_view(), name='toggle-status'),
    path('users/<int:id>/verify/', AdminVerifyUserView.as_view(), name='verify-user'),
    
    # Activity Logs
    path('activity-logs/', AdminActivityLogListView.as_view(), name='activity-logs'),
]