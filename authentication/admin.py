"""
admin.py
---------
This module registers the custom User model for Django's admin interface.
It extends Django's built-in UserAdmin to properly support:

- Email-based authentication
- Additional user attributes (full_name, phone, accepted_terms)
- Custom permission fields
- OTP-based verification state
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    """
    Custom configuration for displaying and managing User model entries
    in the Django admin dashboard.

    The default Django UserAdmin is modified to accommodate:
    - Email as the primary login field
    - Custom fields including phone number and verification status
    """

    model = User

    # Columns displayed on the user list page
    list_display = ("email", "full_name", "phone", "is_verified", "is_staff", "is_active")

    # Filters available in the right sidebar
    list_filter = ("is_verified", "is_staff", "is_active")

    # Enable searching based on key fields
    search_fields = ("email", "full_name", "phone")

    # Default ordering of user entries
    ordering = ("email",)

    # Field organization when editing an existing user
    fieldsets = (
        ("Login Credentials", {
            "fields": ("email", "password")
        }),
        ("Personal Information", {
            "fields": ("full_name", "phone", "accepted_terms")
        }),
        ("Permissions and Status", {
            "fields": ("is_verified", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")
        }),
        ("Important Dates", {
            "fields": ("last_login",)
        }),
    )

    # Fields displayed when creating a new user via admin
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "full_name",
                "email",
                "phone",
                "accepted_terms",
                "password",           # changed from password1 & password2
                "is_verified",
                "is_staff",
                "is_superuser"
            ),
        }),
    )

# Register the custom User model with the customized UserAdmin
admin.site.register(User, UserAdmin)
