"""
admin_panel/views.py
--------------------
API views for admin panel operations.
"""

from rest_framework import generics, status
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
from .models import AdminActivityLog
from .serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminActivityLogSerializer,
)
from .permissions import IsAdminUser
from .utils import log_admin_action

class AdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminLoginView(generics.GenericAPIView):
    """
    Admin-specific login endpoint.
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
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
        })

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
            action='update',
            description=f"Manually verified user {user.email}",
            target_user=user,
            request=request
        )
        
        return Response({
            "message": "User verified successfully.",
            "is_verified": user.is_verified
        })

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
        admin_id = self.request.query_params.get('admin_id', None)
        if admin_id:
            queryset = queryset.filter(admin_user_id=admin_id)
        
        # Filter by action type
        action = self.request.query_params.get('action', None)
        if action:
            queryset = queryset.filter(action=action)
        
        return queryset.order_by('-timestamp')