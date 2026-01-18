# disease/admin.py
from django.contrib import admin
from .models import ScanResult

@admin.register(ScanResult)
class ScanResultAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "crop_type",
        "disease",
        "confidence",
        "severity",
        "created_at",
    )
    list_filter = ("crop_type", "severity", "created_at")
    search_fields = ("crop_type", "disease")
