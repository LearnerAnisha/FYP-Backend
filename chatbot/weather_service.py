import requests
from datetime import datetime, timedelta
from django.conf import settings
from .models import WeatherData

class WeatherService:
    """
    Handles all weather-related API calls
    Uses OpenWeatherMap API (you can use any weather API)
    """
    
    def __init__(self):
        self.api_key = settings.WEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    def get_weather_data(self, location):
        """
        Gets current weather and 5-day forecast
        First checks cache, then fetches from API if needed
        """
        # Check if we have recent cached data (less than 1 hour old)
        cached = WeatherData.objects.filter(
            location=location,
            fetched_at__gte=datetime.now() - timedelta(hours=1)
        ).first()
        
        if cached:
            return {
                'current': cached.current_weather,
                'forecast': cached.forecast_data
            }
        
        # Fetch fresh data from API
        current_weather = self._get_current_weather(location)
        forecast = self._get_5day_forecast(location)
        
        # Save to database for caching
        WeatherData.objects.create(
            location=location,
            current_weather=current_weather,
            forecast_data=forecast
        )
        
        return {
            'current': current_weather,
            'forecast': forecast
        }
    
    def _get_current_weather(self, location):
        """Fetches current weather from API"""
        url = f"{self.base_url}/weather"
        params = {
            'q': location,
            'appid': self.api_key,
            'units': 'metric'  # Use Celsius
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract relevant information
            return {
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'],
                'wind_speed': data['wind']['speed'],
                'location': data['name']
            }
        except Exception as e:
            raise Exception(f"Error fetching current weather: {str(e)}")
    
    def _get_5day_forecast(self, location):
        """Fetches 5-day forecast from API"""
        url = f"{self.base_url}/forecast"
        params = {
            'q': location,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Process forecast data - group by day
            daily_forecasts = []
            current_date = None
            daily_data = []
            
            for item in data['list']:
                date = datetime.fromtimestamp(item['dt']).date()
                
                if current_date != date:
                    if daily_data:
                        daily_forecasts.append(self._process_day(daily_data))
                    current_date = date
                    daily_data = [item]
                else:
                    daily_data.append(item)
            
            # Add last day
            if daily_data:
                daily_forecasts.append(self._process_day(daily_data))
            
            return daily_forecasts[:5]  # Return only 5 days
        
        except Exception as e:
            raise Exception(f"Error fetching forecast: {str(e)}")
    
    def _process_day(self, day_data):
        """Processes data for a single day"""
        temps = [item['main']['temp'] for item in day_data]
        
        return {
            'date': datetime.fromtimestamp(day_data[0]['dt']).strftime('%Y-%m-%d'),
            'temp_min': min(temps),
            'temp_max': max(temps),
            'description': day_data[0]['weather'][0]['description'],
            'humidity': sum(item['main']['humidity'] for item in day_data) / len(day_data),
            'precipitation_chance': day_data[0].get('pop', 0) * 100  # Probability of precipitation
        }