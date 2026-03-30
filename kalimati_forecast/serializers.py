from rest_framework import serializers
from .models import PriceRecord, ForecastResult, ModelMetric


class PriceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceRecord
        fields = '__all__'


class ForecastResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForecastResult
        fields = '__all__'


class ModelMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelMetric
        fields = '__all__'


class ForecastRequestSerializer(serializers.Serializer):
    commodity = serializers.CharField(max_length=100)
    days = serializers.IntegerField(min_value=1, max_value=30, default=7)
    model = serializers.ChoiceField(
        choices=['arima', 'sarimax', 'lgbm', 'ensemble'],
        default='ensemble'
    )


class UploadCSVSerializer(serializers.Serializer):
    file = serializers.FileField()
    commodity = serializers.CharField(required=False, allow_blank=True)


class RetrainSerializer(serializers.Serializer):
    commodity = serializers.CharField(required=False, allow_blank=True, help_text="Leave blank to retrain all.")