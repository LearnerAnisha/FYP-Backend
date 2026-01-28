"""
admin_panel/serializers.py
--------------------------
Serializers for admin panel operations with your existing models.
"""

from rest_framework import serializers
from authentication.models import User, FarmerProfile
from chatbot.models import ChatConversation, ChatMessage, WeatherData, CropSuggestion
from CropDiseaseDetection.models import ScanResult
from .models import AdminActivityLog
from django.utils.timezone import now

# ========== USER MANAGEMENT SERIALIZERS ==========

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
            'is_superuser',
            'date_joined',
            'last_login',
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

# ========== CHATBOT SERIALIZERS ==========

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'conversation', 'role', 'content', 'timestamp']
        read_only_fields = ['timestamp']

class ChatConversationListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatConversation
        fields = [
            'id', 'user', 'user_name', 'user_email', 'session_id',
            'created_at', 'updated_at', 'message_count', 'last_message'
        ]
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'content': last_msg.content[:100],
                'timestamp': last_msg.timestamp
            }
        return None

class ChatConversationDetailSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    
    class Meta:
        model = ChatConversation
        fields = [
            'id', 'user', 'user_name', 'user_email', 'session_id',
            'created_at', 'updated_at', 'messages'
        ]

class CropSuggestionSerializer(serializers.ModelSerializer):
    conversation_session_id = serializers.CharField(source='conversation.session_id', read_only=True)
    user_email = serializers.SerializerMethodField()
    
    class Meta:
        model = CropSuggestion
        fields = [
            'id', 'conversation', 'conversation_session_id', 'user_email',
            'crop_name', 'growth_stage', 'weather_conditions',
            'suggestion', 'created_at'
        ]
    
    def get_user_email(self, obj):
        if obj.conversation and obj.conversation.user:
            return obj.conversation.user.email
        return None

class WeatherDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherData
        fields = [
            'id', 'location', 'current_weather', 'forecast_data', 'fetched_at'
        ]

# ========== CROP DISEASE SERIALIZERS ==========

class ScanResultListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanResult
        fields = [
            'id', 'image', 'crop_type', 'disease', 'confidence',
            'severity', 'created_at'
        ]

class ScanResultDetailSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ScanResult
        fields = [
            'id', 'image', 'image_url', 'crop_type', 'disease',
            'confidence', 'severity', 'created_at'
        ]
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None

# ========== ADMIN ACTIVITY LOG SERIALIZERS ==========

class AdminActivityLogSerializer(serializers.ModelSerializer):
    admin_user_name = serializers.CharField(source='admin_user.full_name', read_only=True, allow_null=True)
    admin_user_email = serializers.CharField(source='admin_user.email', read_only=True, allow_null=True)
    target_user_name = serializers.CharField(source='target_user.full_name', read_only=True, allow_null=True)
    target_user_email = serializers.CharField(source='target_user.email', read_only=True, allow_null=True)
    
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
            'target_user_email',
            'description',
            'ip_address',
            'timestamp',
            'metadata',
        ]
        read_only_fields = ['timestamp']