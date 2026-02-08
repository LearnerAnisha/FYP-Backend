"""
admin_panel/views.py
--------------------
API views for admin panel operations with your existing models.
"""

from rest_framework import generics, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from authentication.models import User, FarmerProfile
from authentication.serializers import LoginSerializer
from chatbot.models import ChatConversation, ChatMessage, WeatherData, CropSuggestion
from CropDiseaseDetection.models import ScanResult
from .models import AdminActivityLog
from .serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminActivityLogSerializer,
    ChatConversationListSerializer,
    ChatConversationDetailSerializer,
    ChatMessageSerializer,
    CropSuggestionSerializer,
    WeatherDataSerializer,
    ScanResultListSerializer,
    ScanResultDetailSerializer,
)
from price_predictor.models import MasterProduct, DailyPriceHistory
from price_predictor.views import (
    FetchMarketPriceAPIView,
    MarketPriceAnalysisAPIView,
    PriceStatsAPIView,
)
from .serializers import (
    AdminMasterProductSerializer,
    AdminDailyPriceHistorySerializer,
)

from .permissions import IsAdminUser
from .utils import log_admin_action

class AdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# ========== AUTHENTICATION ==========

class AdminLoginView(generics.GenericAPIView):
    """
    Admin-specific login endpoint.
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        login_data = {
    "identifier": request.data.get("email"),
    "password": request.data.get("password"),
}
        serializer = self.get_serializer(data=login_data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data["user"]
        
        # Check if user is staff or superuser
        if not (user.is_staff or user.is_superuser):
            return Response(
                {"message": "Access denied. Admin privileges required."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not user.is_verified:
            return Response(
                {"message": "Email verification required."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Log admin login
        log_admin_action(
            admin_user=user,
            action='login',
            description=f"Admin {user.email} logged in",
            request=request
        )
        
        refresh = RefreshToken.for_user(user)
        
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser
                }
            },
            status=status.HTTP_200_OK
        )

# ========== DASHBOARD ==========

class AdminDashboardStatsView(APIView):
    """
    Get dashboard statistics.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        # Basic counts
        total_users = User.objects.count()
        verified_users = User.objects.filter(is_verified=True).count()
        active_users = User.objects.filter(is_active=True).count()
        staff_users = User.objects.filter(is_staff=True).count()
        
        # Time-based statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        users_today = User.objects.filter(date_joined__date=today).count()
        users_this_week = User.objects.filter(date_joined__date__gte=week_ago).count()
        users_this_month = User.objects.filter(date_joined__date__gte=month_ago).count()
        
        # Farmer statistics
        total_farmers = FarmerProfile.objects.count()
        
        # Chatbot statistics
        total_conversations = ChatConversation.objects.count()
        total_messages = ChatMessage.objects.count()
        
        # Disease scan statistics
        total_scans = ScanResult.objects.count()
        
        return Response({
            "overview": {
                "total_users": total_users,
                "verified_users": verified_users,
                "unverified_users": total_users - verified_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "staff_users": staff_users,
                "total_farmers": total_farmers,
            },
            "registrations": {
                "today": users_today,
                "this_week": users_this_week,
                "this_month": users_this_month,
            },
            "chatbot": {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
            },
            "disease_detection": {
                "total_scans": total_scans,
            }
        })

# ========== USER MANAGEMENT ==========

# Add this new view for creating users
class AdminCreateUserView(generics.CreateAPIView):
    """
    Admin endpoint to create a new user.
    """
    serializer_class = AdminUserDetailSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def create(self, request, *args, **kwargs):
        # Extract data
        data = request.data.copy()
        password = data.pop('password', None)
        
        if not password:
            return Response(
                {"password": ["Password is required."]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use serializer for validation
        serializer = self.get_serializer(data=data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create user
        try:
            user = User.objects.create_user(
                full_name=serializer.validated_data['full_name'],
                email=serializer.validated_data['email'],
                phone=serializer.validated_data['phone'],
                password=password,
                is_verified=serializer.validated_data.get('is_verified', False),
                is_active=serializer.validated_data.get('is_active', True),
                is_staff=serializer.validated_data.get('is_staff', False),
                is_superuser=serializer.validated_data.get('is_superuser', False),
                accepted_terms=serializer.validated_data.get('accepted_terms', True)
            )
            
            # Handle farmer profile if provided
            farmer_data = request.data.get('farmer_profile')
            if farmer_data:
                FarmerProfile.objects.create(user=user, **farmer_data)
            
            # Log action
            log_admin_action(
                admin_user=request.user,
                action='create',
                description=f"Created new user {user.email}",
                target_user=user,
                request=request
            )
            
            return Response(
                {
                    "message": "User created successfully.",
                    "user": AdminUserDetailSerializer(user).data
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class AdminUserListView(generics.ListAPIView):
    """
    List all users with search and filtering.
    """
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = AdminPagination
    
    def get_queryset(self):
        queryset = User.objects.all().select_related('farmer_profile')
        
        # Search by name, email, or phone
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        
        # Filter by verification status
        is_verified = self.request.query_params.get('is_verified', None)
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == 'true')
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by staff status
        is_staff = self.request.query_params.get('is_staff', None)
        if is_staff is not None:
            queryset = queryset.filter(is_staff=is_staff.lower() == 'true')
        
        # Sorting
        sort_by = self.request.query_params.get('sort_by', '-date_joined')
        queryset = queryset.order_by(sort_by)
        
        return queryset

class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific user.
    """
    queryset = User.objects.all()
    serializer_class = AdminUserDetailSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'id'
    
    def perform_update(self, serializer):
        user = serializer.save()
        log_admin_action(
            admin_user=self.request.user,
            action='update',
            description=f"Updated user {user.email}",
            target_user=user,
            request=self.request
        )
    
    def perform_destroy(self, instance):
        log_admin_action(
            admin_user=self.request.user,
            action='delete',
            description=f"Deleted user {instance.email}",
            target_user=instance,
            request=self.request
        )
        instance.delete()

class AdminToggleUserStatusView(APIView):
    """
    Toggle user active status (activate/deactivate).
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def patch(self, request, id):
        try:
            user = User.objects.get(id=id)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prevent deactivating yourself
        if user.id == request.user.id:
            return Response(
                {"message": "You cannot deactivate your own account."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_active = not user.is_active
        user.save()
        
        action = 'activate' if user.is_active else 'deactivate'
        log_admin_action(
            admin_user=request.user,
            action=action,
            description=f"{'Activated' if user.is_active else 'Deactivated'} user {user.email}",
            target_user=user,
            request=request
        )
        
        return Response({
            "message": f"User {'activated' if user.is_active else 'deactivated'} successfully.",
            "is_active": user.is_active
        })

class AdminVerifyUserView(APIView):
    """
    Manually verify a user's email.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def patch(self, request, id):
        try:
            user = User.objects.get(id=id)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if user.is_verified:
            return Response(
                {"message": "User is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_verified = True
        user.save()
        
        log_admin_action(
            admin_user=request.user,
            action='verify',
            description=f"Manually verified user {user.email}",
            target_user=user,
            request=request
        )
        
        return Response({
            "message": "User verified successfully.",
            "is_verified": user.is_verified
        })

# ========== CHATBOT MANAGEMENT ==========

class ChatConversationListView(generics.ListAPIView):
    serializer_class = ChatConversationListSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = AdminPagination
    
    def get_queryset(self):
        queryset = ChatConversation.objects.all().select_related('user').prefetch_related('messages')
        
        # Search by session_id or user email
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(session_id__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__full_name__icontains=search)
            )
        
        return queryset.order_by('-updated_at')

class ChatConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ChatConversation.objects.all()
    serializer_class = ChatConversationDetailSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def perform_destroy(self, instance):
        log_admin_action(
            admin_user=self.request.user,
            action='delete',
            description=f"Deleted conversation {instance.session_id}",
            target_user=instance.user,
            request=self.request
        )
        instance.delete()

class ChatMessageListView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = AdminPagination
    
    def get_queryset(self):
        queryset = ChatMessage.objects.all().select_related('conversation')
        
        conversation_id = self.request.query_params.get('conversation_id')
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        return queryset.order_by('-timestamp')

class CropSuggestionListView(generics.ListAPIView):
    serializer_class = CropSuggestionSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = AdminPagination
    
    def get_queryset(self):
        queryset = CropSuggestion.objects.all().select_related('conversation', 'conversation__user')
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(crop_name__icontains=search) |
                Q(growth_stage__icontains=search)
            )
        
        return queryset.order_by('-created_at')

class WeatherDataListView(generics.ListAPIView):
    serializer_class = WeatherDataSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = AdminPagination
    
    def get_queryset(self):
        queryset = WeatherData.objects.all()
        
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        return queryset.order_by('-fetched_at')

# ========== CROP DISEASE DETECTION ==========

class ScanResultListView(generics.ListAPIView):
    serializer_class = ScanResultListSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = AdminPagination
    
    def get_queryset(self):
        queryset = ScanResult.objects.all()
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(crop_type__icontains=search) |
                Q(disease__icontains=search)
            )
        
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        return queryset.order_by('-created_at')

class ScanResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ScanResult.objects.all()
    serializer_class = ScanResultDetailSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

# ========== ACTIVITY LOGS ==========

class AdminActivityLogListView(generics.ListAPIView):
    """
    List all admin activity logs.
    """
    serializer_class = AdminActivityLogSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = AdminPagination
    
    def get_queryset(self):
        queryset = AdminActivityLog.objects.all().select_related(
            'admin_user', 'target_user'
        )
        
        # Filter by admin user
        admin_id = self.request.query_params.get('admin_id')
        if admin_id:
            queryset = queryset.filter(admin_user_id=admin_id)
        
        # Filter by action type
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Search in description
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(description__icontains=search)
        
        return queryset.order_by('-timestamp')
    
# ========== PRICE PREDICTOR MANAGEMENT ==========

class AdminMasterProductListView(generics.ListAPIView):
    """
    Admin view: list latest commodity prices with search and filters.
    """
    serializer_class = AdminMasterProductSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = AdminPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Enable search on commodity name
    search_fields = ['commodityname', 'commodityunit']
    
    # Enable ordering
    ordering_fields = ['commodityname', 'min_price', 'max_price', 'avg_price', 'last_price', 'last_update']
    ordering = ['commodityname']  # default ordering

    queryset = MasterProduct.objects.all()

class AdminMasterProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin view: retrieve, update, or delete a specific product.
    """
    queryset = MasterProduct.objects.all()
    serializer_class = AdminMasterProductSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'id'
    
    def perform_update(self, serializer):
        product = serializer.save()
        log_admin_action(
            admin_user=self.request.user,
            action='update',
            description=f"Updated product {product.commodityname}",
            request=self.request
        )
    
    def perform_destroy(self, instance):
        log_admin_action(
            admin_user=self.request.user,
            action='delete',
            description=f"Deleted product {instance.commodityname}",
            request=self.request
        )
        instance.delete()

class AdminDailyPriceHistoryListView(generics.ListAPIView):
    """
    Admin view: daily historical price records with search and filters.
    """
    serializer_class = AdminDailyPriceHistorySerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = AdminPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Enable search on product name
    search_fields = ['product__commodityname']
    
    # Enable ordering
    ordering_fields = ['date', 'avg_price', 'min_price', 'max_price']
    ordering = ['-date']  # default ordering (newest first)

    queryset = DailyPriceHistory.objects.select_related('product').all()

class AdminDailyPriceHistoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin view: retrieve, update, or delete a specific price history entry.
    """
    queryset = DailyPriceHistory.objects.select_related('product').all()
    serializer_class = AdminDailyPriceHistorySerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'id'
    
    def perform_update(self, serializer):
        entry = serializer.save()
        log_admin_action(
            admin_user=self.request.user,
            action='update',
            description=f"Updated price history for {entry.product.commodityname} on {entry.date}",
            request=self.request
        )
    
    def perform_destroy(self, instance):
        log_admin_action(
            admin_user=self.request.user,
            action='delete',
            description=f"Deleted price history for {instance.product.commodityname} on {instance.date}",
            request=self.request
        )
        instance.delete()

class AdminMarketPriceAnalysisView(MarketPriceAnalysisAPIView):
    """
    Admin view: market trend analysis.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

class AdminFetchMarketPricesView(FetchMarketPriceAPIView):
    """
    Admin-only trigger for fetching market prices.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

class AdminPriceStatsView(PriceStatsAPIView):
    """
    Admin-only price dashboard stats.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]