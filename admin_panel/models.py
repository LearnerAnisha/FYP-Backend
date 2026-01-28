"""
admin_panel/models.py
---------------------
Models for admin activity logging and management.
"""

from django.db import models
from django.conf import settings

class AdminActivityLog(models.Model):
    """
    Logs all admin actions for auditing purposes.
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('activate', 'Activate'),
        ('deactivate', 'Deactivate'),
        ('verify', 'Verify'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View'),
    ]
    
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_actions'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions_received'
    )
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(null=True, blank=True)  # Store additional context
    
    class Meta:
        ordering = ['-timestamp']
        db_table = 'admin_activity_logs'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['admin_user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.admin_user} - {self.action} - {self.timestamp}"