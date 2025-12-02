from rest_framework import serializers
from .models import MarketPrice

class MarketPriceSerializer(serializers.ModelSerializer):
    """
    Serializer to convert MarketPrice model to JSON format for API responses.
    """
    class Meta:
        model = MarketPrice
        fields = "__all__"
