from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ("email", "full_name", "phone", "is_verified", "is_staff", "is_active")
    list_filter = ("is_verified", "is_staff", "is_active")
    search_fields = ("email", "full_name", "phone")
    ordering = ("email",)

    fieldsets = (
        ("Login Credentials", {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("full_name", "phone", "accepted_terms")}),
        ("Permissions", {"fields": ("is_verified", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important Dates", {"fields": ("last_login",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("full_name", "email", "phone", "password1", "password2", "is_verified", "is_staff", "is_superuser"),
        }),
    )

admin.site.register(User, UserAdmin)
