"""
models.py
---------
This module defines the database models used for authentication.

It contains:
1. A custom User model that uses email as the primary identifier.
2. An EmailOTP model for secure email-based OTP verification.

The design follows modern authentication practices where:
- Email replaces username
- Users must verify their email before login
- OTPs are short-lived and single-use
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta
import random

class UserManager(BaseUserManager):
    """
    Custom user manager that supports email-based authentication.
    """

    def create_user(self, full_name, email, phone, password=None, **extra_fields):
        """
        Creates and saves a regular user.

        Required fields:
        - full_name
        - email
        - phone
        """
        if not email:
            raise ValueError("Email is required")
        if not phone:
            raise ValueError("Phone number is required")
        if not full_name:
            raise ValueError("Full name is required")

        email = self.normalize_email(email)
        user = self.model(
            full_name=full_name,
            email=email,
            phone=phone,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, full_name, email, phone, password=None, **extra_fields):
        """
        Creates and saves a superuser with administrative privileges.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)

        return self.create_user(full_name, email, phone, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model.

    Key characteristics:
    - Email is used as USERNAME_FIELD
    - Account access is restricted until email is verified via OTP
    """

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True)

    accepted_terms = models.BooleanField(default=False)

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(auto_now_add=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "phone"]

    objects = UserManager()

    def __str__(self):
        return self.email

class FarmerProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="farmer_profile"
    )

    farm_size = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    experience = models.PositiveIntegerField(null=True, blank=True)
    crop_types = models.CharField(max_length=255, blank=True)
    language = models.CharField(max_length=20, default="nepali")
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"FarmerProfile of {self.user.email}"

class EmailOTP(models.Model):
    """
    Model to store email-based One-Time Passwords (OTP).

    Security features:
    - One OTP per user
    - Automatic expiration (10 minutes)
    - Deleted after successful verification
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="email_otp"
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        """
        Checks whether the OTP has expired.

        Returns:
            bool: True if OTP is older than 10 minutes.
        """
        expiry_time = self.created_at + timedelta(minutes=10)
        return timezone.now() > expiry_time

    def __str__(self):
        return f"OTP for {self.user.email}"

def generate_otp():
    """
    Generates a cryptographically random 6-digit OTP.

    Returns:
        str: A 6-digit numeric OTP.
    """
    return str(random.randint(100000, 999999))

