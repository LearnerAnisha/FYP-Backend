"""
admin_panel/serializers.py
--------------------------
Serializers for admin panel operations.
"""

from rest_framework import serializers
from authentication.models import User, FarmerProfile
from .models import AdminActivityLog
from django.utils.timezone import now

class AdminFarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        fields = [
            'farm_size',
            'experience',
            'crop_types',
            'language',
            'bio',
        ]

class AdminUserListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for user listing.
    """
    has_farmer_profile = serializers.SerializerMethodField()
    days_active = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'full_name',
            'email',
            'phone',
            'is_verified',
            'is_active',
            'is_staff',
            'date_joined',
            'has_farmer_profile',
            'days_active',
        ]
    
    def get_has_farmer_profile(self, obj):
        return hasattr(obj, 'farmer_profile')
    
    def get_days_active(self, obj):
        return (now().date() - obj.date_joined.date()).days + 1

class AdminUserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single user view/edit.
    """
    farmer_profile = AdminFarmerProfileSerializer(required=False)
    last_login = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id',
            'full_name',
            'email',
            'phone',
            'avatar',
            'is_verified',
            'is_active',
            'is_staff',
            'is_superuser',
            'date_joined',
            'last_login',
            'accepted_terms',
            'farmer_profile',
        ]
        read_only_fields = ['email', 'date_joined', 'last_login']
    
    def update(self, instance, validated_data):
        farmer_data = validated_data.pop('farmer_profile', None)
        
        # Update User fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update or create FarmerProfile
        if farmer_data:
            profile, _ = FarmerProfile.objects.get_or_create(user=instance)
            for attr, value in farmer_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance

class AdminActivityLogSerializer(serializers.ModelSerializer):
    admin_user_name = serializers.CharField(source='admin_user.full_name', read_only=True)
    admin_user_email = serializers.CharField(source='admin_user.email', read_only=True)
    target_user_name = serializers.CharField(source='target_user.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = AdminActivityLog
        fields = [
            'id',
            'admin_user',
            'admin_user_name',
            'admin_user_email',
            'action',
            'target_user',
            'target_user_name',
            'description',
            'ip_address',
            'timestamp',
        ]
        read_only_fields = ['timestamp']