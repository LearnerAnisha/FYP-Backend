"""
admin_panel/serializers.py
--------------------------
Serializers for admin panel operations with your existing models.
"""

from rest_framework import serializers
import re
from django.utils.timezone import now
from authentication.models import User, FarmerProfile
from chatbot.models import ChatConversation, ChatMessage, WeatherData, CropSuggestion
from price_predictor.models import MasterProduct, DailyPriceHistory
from CropDiseaseDetection.models import ScanResult
from .models import AdminActivityLog

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
    Detailed serializer for single user view/edit/create.
    """
    farmer_profile = AdminFarmerProfileSerializer(required=False)
    last_login = serializers.DateTimeField(read_only=True)
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'id',
            'full_name',
            'email',
            'phone',
            'password',
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
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def validate_full_name(self, value):
        """Validate full name format"""
        value = value.strip()
        if len(value.split()) < 2:
            raise serializers.ValidationError(
                "Full name must include at least first and last name."
            )
        if not re.match(r"^[A-Za-z ]+$", value):
            raise serializers.ValidationError(
                "Full name can only contain letters and spaces."
            )
        return value
    
    def validate_phone(self, value):
        """Validate Nepal phone number format"""
        if not re.match(r"^(98|97)\d{8}$", value):
            raise serializers.ValidationError(
                "Phone number must start with 98 or 97 and contain exactly 10 digits."
            )
        return value
    
    def validate_email(self, value):
        """Check for duplicate email (only on create)"""
        if self.instance is None:  # Creating new user
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError(
                    "An account with this email already exists."
                )
        return value
    
    def validate_password(self, value):
        """Strong password validation"""
        if not value:
            return value
            
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long."
            )
        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter."
            )
        if not re.search(r"[0-9]", value):
            raise serializers.ValidationError(
                "Password must contain at least one number."
            )
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise serializers.ValidationError(
                "Password must contain at least one special character."
            )
        return value
    
    def update(self, instance, validated_data):
        farmer_data = validated_data.pop('farmer_profile', None)
        password = validated_data.pop('password', None)
        
        # Update User fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update password if provided
        if password:
            instance.set_password(password)
        
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

# ========== PRICE PREDICTOR SERIALIZERS ==========

class AdminMasterProductSerializer(serializers.ModelSerializer):
    """Admin serializer for MasterProduct with full CRUD support."""
    class Meta:
        model = MasterProduct
        fields = "__all__"
        read_only_fields = ['insert_date', 'last_update']

class AdminDailyPriceHistorySerializer(serializers.ModelSerializer):
    """Admin serializer for DailyPriceHistory with product name."""
    product_name = serializers.CharField(source="product.commodityname", read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    
    class Meta:
        model = DailyPriceHistory
        fields = [
            "id",
            "product",
            "product_id",
            "product_name",
            "date",
            "min_price",
            "max_price",
            "avg_price",
        ]