from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ["id", "transaction_uuid", "total_amount", "status", "esewa_ref_id", "created_at"]
    list_filter   = ["status", "created_at"]
    search_fields = ["transaction_uuid", "esewa_ref_id"]
    readonly_fields = [
        "transaction_uuid", "amount", "tax_amount", "service_charge",
        "delivery_charge", "total_amount", "esewa_ref_id",
        "esewa_raw_response", "created_at", "updated_at",
    ]
    ordering = ["-created_at"]
