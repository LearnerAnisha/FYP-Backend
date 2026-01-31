from rest_framework import serializers

class WeatherRequestSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()
