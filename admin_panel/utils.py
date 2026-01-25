"""
admin_panel/utils.py
--------------------
Utility functions for admin panel.
"""

from .models import AdminActivityLog

def log_admin_action(admin_user, action, description, target_user=None, request=None):
    """
    Log an admin action for auditing.
    """
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
    
    AdminActivityLog.objects.create(
        admin_user=admin_user,
        action=action,
        target_user=target_user,
        description=description,
        ip_address=ip_address
    )