"""
admin_panel/permissions.py
--------------------------
Custom permissions for admin panel.
"""

from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Permission to check if user is staff or superuser.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_staff or request.user.is_superuser)
        )