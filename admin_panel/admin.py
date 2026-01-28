from django.contrib import admin
from .models import AdminActivityLog

@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    list_display = ['admin_user', 'action', 'target_user', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp']
    search_fields = ['admin_user__email', 'target_user__email', 'description']
    readonly_fields = ['admin_user', 'action', 'target_user', 'description', 'ip_address', 'timestamp', 'metadata']
    list_per_page = 50
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False