import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETE = "COMPLETE", "Complete"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    # Link to user (nullable so existing anonymous payments don't break)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )

    transaction_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    esewa_ref_id = models.CharField(max_length=100, blank=True, null=True)
    esewa_raw_response = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.pk} | {self.transaction_uuid} | {self.status}"


class Subscription(models.Model):
    class Plan(models.TextChoices):
        FREE = "FREE", "Free"  # ← removed BASIC/PREMIUM, kept only these two
        PRO = "PRO", "Pro"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription"
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )
    plan = models.CharField(max_length=10, choices=Plan.choices, default=Plan.FREE)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_pro(self):
        return (
            self.plan == self.Plan.PRO
            and self.is_active
            and (self.expires_at is None or self.expires_at > timezone.now())
        )

    def __str__(self):
        return (
            f"Subscription({self.user.email} | {self.plan} | active={self.is_active})"
        )


# Daily request limits for FREE users — PRO users have unlimited access
DAILY_LIMITS = {
    "disease_detection": 5,
    "weather_irrigation": 10,
    "price_forecast": 5,
    "chatbot": 10,
}


class DailyUsage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_usages"
    )
    feature = models.CharField(max_length=50)  # one of the keys in DAILY_LIMITS
    date = models.DateField(default=timezone.now)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "feature", "date")

    def __str__(self):
        return f"{self.user.email} | {self.feature} | {self.date} | {self.count}"
