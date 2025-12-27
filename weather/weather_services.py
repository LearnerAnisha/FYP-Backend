import requests
from django.conf import settings

BASE_URL = "https://api.openweathermap.org/data/2.5"


class WeatherServiceError(Exception):
    """
    Custom exception for weather service related failures
    """
    pass


def get_weather_data(city=None, lat=None, lon=None):
    """
    Fetch current weather and 5-day forecast using
    latitude/longitude (preferred) or city name (fallback)
    """

    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        raise WeatherServiceError("Weather API key not configured")

    params = {
        "appid": api_key,
        "units": "metric",
    }

    # ✅ Prefer lat/lon (most reliable)
    if lat and lon:
        params["lat"] = lat
        params["lon"] = lon
    else:
        params["q"] = city or "Kathmandu"

    try:
        # Current weather
        current_response = requests.get(
            f"{BASE_URL}/weather",
            params=params,
            timeout=10
        )
        current_response.raise_for_status()

        # 5-day forecast
        forecast_response = requests.get(
            f"{BASE_URL}/forecast",
            params=params,
            timeout=10
        )
        forecast_response.raise_for_status()

        return current_response.json(), forecast_response.json()

    except requests.exceptions.HTTPError as e:
        raise WeatherServiceError(
            "Weather data could not be retrieved for the given location"
        )

    except requests.exceptions.RequestException:
        raise WeatherServiceError(
            "External weather service is unavailable"
        )


def format_forecast(forecast_list):
    """
    Convert 3-hour interval forecast into daily summary (5 days)
    """

    daily_data = {}

    for item in forecast_list:
        date = item["dt_txt"].split(" ")[0]

        if date not in daily_data:
            daily_data[date] = {
                "temperature": round(item["main"]["temp"]),
                "condition": item["weather"][0]["main"],
                "rain_probability": int(item.get("pop", 0) * 100),
            }

    labels = ["Today", "Tomorrow", "Wed", "Thu", "Fri"]
    formatted = list(daily_data.values())[:5]

    for index, day in enumerate(formatted):
        day["day"] = labels[index]

    return formatted


def build_weather_response(city=None, lat=None, lon=None):
    """
    Build final API response for frontend consumption
    """

    current, forecast = get_weather_data(
        city=city,
        lat=lat,
        lon=lon
    )

    return {
        "city": city or "Kathmandu",
        "current": {
            "temperature": round(current["main"]["temp"]),
            "humidity": current["main"]["humidity"],
            "rainfall": current.get("rain", {}).get("1h", 0),
            "wind_speed": current.get("wind", {}).get("speed", 0),
            "condition": current["weather"][0]["main"],
        },
        "forecast": format_forecast(forecast["list"]),
    }