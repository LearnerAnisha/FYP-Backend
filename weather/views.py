from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from weather.weather_services import (
    build_weather_response,
    WeatherServiceError,
)
class CurrentWeatherAPIView(APIView):
    """
    GET /api/weather/current/?lat=27.7&lon=85.3
    """

    permission_classes = [AllowAny]

    def get(self, request):
        lat = request.GET.get("lat")
        lon = request.GET.get("lon")

        try:
            data = build_weather_response(
                lat=lat,
                lon=lon
            )
            return Response(data, status=status.HTTP_200_OK)

        except WeatherServiceError as error:
            return Response(
                {
                    "error": True,
                    "message": str(error),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception:
            return Response(
                {
                    "error": True,
                    "message": "Internal server error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )