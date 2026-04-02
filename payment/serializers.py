from decimal import Decimal
from rest_framework import serializers
from .models import Payment, Subscription

MAX_AMOUNT = Decimal("500000.00")
MIN_AMOUNT = Decimal("1.00")

class PaymentInitSerializer(serializers.Serializer):
    """
    Validates incoming payment initiation request from client.
    """

    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), required=False
    )
    service_charge = serializers.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), required=False
    )
    delivery_charge = serializers.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), required=False
    )

    def validate_amount(self, value):
        if value < MIN_AMOUNT:
            raise serializers.ValidationError(
                f"Amount must be at least NPR {MIN_AMOUNT}. You provided NPR {value}."
            )
        if value > MAX_AMOUNT:
            raise serializers.ValidationError(
                f"Amount cannot exceed NPR {MAX_AMOUNT:,}. You provided NPR {value:,}."
            )
        return value

    def validate_tax_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Tax amount cannot be negative.")
        return value

    def validate_service_charge(self, value):
        if value < 0:
            raise serializers.ValidationError("Service charge cannot be negative.")
        return value

    def validate_delivery_charge(self, value):
        if value < 0:
            raise serializers.ValidationError("Delivery charge cannot be negative.")
        return value

    def validate(self, data):
        total = (
            data["amount"]
            + data.get("tax_amount", Decimal("0"))
            + data.get("service_charge", Decimal("0"))
            + data.get("delivery_charge", Decimal("0"))
        )
        if total > MAX_AMOUNT:
            raise serializers.ValidationError(
                f"Total amount (NPR {total:,}) exceeds the maximum allowed limit of NPR {MAX_AMOUNT:,}."
            )
        data["total_amount"] = total
        return data


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializes Payment model for list/detail views.
    """

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "transaction_uuid",
            "amount",
            "tax_amount",
            "service_charge",
            "delivery_charge",
            "total_amount",
            "status",
            "status_display",
            "esewa_ref_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    payment_uuid = serializers.UUIDField(
        source="payment.transaction_uuid", read_only=True, allow_null=True
    )
    plan_display = serializers.CharField(source="get_plan_display", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "payment",
            "payment_uuid",
            "plan",
            "plan_display",
            "is_active",
            "starts_at",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "starts_at", "created_at", "updated_at"]
