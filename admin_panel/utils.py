from .models import AdminActivityLog

def log_admin_action(admin_user, action, description, target_user=None, request=None, metadata=None):
    """
    Log an admin action for auditing.
    
    Args:
        admin_user: User performing the action
        action: Type of action (from ACTION_CHOICES)
        description: Description of the action
        target_user: User being affected (optional)
        request: HTTP request object (for IP tracking)
        metadata: Additional data as dict (optional)
    """
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
    
    AdminActivityLog.objects.create(
        admin_user=admin_user,
        action=action,
        target_user=target_user,
        description=description,
        ip_address=ip_address,
        metadata=metadata
    )