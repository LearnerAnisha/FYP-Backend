from rest_framework import serializers
from .models import MasterProduct, DailyPriceHistory
class MasterProductSerializer(serializers.ModelSerializer):
    """Serializer for latest snapshot of commodities."""
    class Meta:
        model = MasterProduct
        fields = "__all__"
class DailyPriceHistorySerializer(serializers.ModelSerializer):
    """Serializer for historical daily price data."""
    product_name = serializers.CharField(source="product.commodityname", read_only=True)
    class Meta:
        model = DailyPriceHistory
        fields = [
            "product_name",
            "date",
            "min_price",
            "max_price",
            "avg_price",
        ]
