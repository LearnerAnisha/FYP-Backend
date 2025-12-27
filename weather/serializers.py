from rest_framework import serializers

class WeatherAdviceRequestSerializer(serializers.Serializer):
    city = serializers.CharField(max_length=100)
    crop = serializers.CharField(max_length=100)
    growth_stage = serializers.CharField(max_length=100)

class WeatherAdviceResponseSerializer(serializers.Serializer):
    city = serializers.CharField()
    temperature = serializers.FloatField()
    humidity = serializers.IntegerField()
    rainfall = serializers.FloatField()

    irrigation_tip = serializers.CharField()
    fertilizer_tip = serializers.CharField()