import uuid
from django.db import models

class Payment(models.Model):
    """
    Stores all payment records initiated through eSewa.
    """

    class Status(models.TextChoices):
        PENDING  = "PENDING",  "Pending"
        COMPLETE = "COMPLETE", "Complete"
        FAILED   = "FAILED",   "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    # ── Identifiers ─────────────────────────────────────────────────────────
    transaction_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Unique transaction ID sent to eSewa.",
    )

    # ── Amount breakdown ─────────────────────────────────────────────────────
    amount          = models.DecimalField(max_digits=12, decimal_places=2, help_text="Base product/service amount.")
    tax_amount      = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Tax component.")
    service_charge  = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Service charge.")
    delivery_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Delivery charge.")
    total_amount    = models.DecimalField(max_digits=12, decimal_places=2, help_text="Sum of all amount fields.")

    # ── Status ───────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # ── eSewa response fields ────────────────────────────────────────────────
    esewa_ref_id        = models.CharField(max_length=100, blank=True, null=True, help_text="Reference ID from eSewa after success.")
    esewa_raw_response  = models.JSONField(blank=True, null=True, help_text="Full raw eSewa verification API response.")

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    # ── Optional: link to your user/order ────────────────────────────────────
    # user  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    # order = models.ForeignKey("orders.Order", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"Payment #{self.pk} | {self.transaction_uuid} | {self.status} | NPR {self.total_amount}"
