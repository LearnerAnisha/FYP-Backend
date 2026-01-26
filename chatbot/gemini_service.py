from django.conf import settings
from google import genai
from PIL import Image


class GeminiService:
    """
    Handles all AI chatbot interactions using Google Gemini 2.5 Flash
    Uses the NEW google-genai SDK (required for Gemini 2.x / 2.5 models)
    """

    def __init__(self):
        # Initialize Gemini client
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Model you actually have access to
        self.model_name = "models/gemini-2.5-flash"

    # MAIN FEATURE: Crop suggestion based on weather
    def get_crop_suggestion(self, crop_name, growth_stage, weather_data):
        prompt = self._create_crop_prompt(crop_name, growth_stage, weather_data)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            return response.text

        except Exception as e:
            raise Exception(f"Error generating crop suggestion: {str(e)}")

    # Prompt builder (unchanged logic)
    def _create_crop_prompt(self, crop_name, growth_stage, weather_data):
        current = weather_data.get("current", {})
        forecast = weather_data.get("forecast", [])

        forecast_text = "\n".join(
            [
                f"- {day['date']}: {day['temp_min']:.1f}°C to {day['temp_max']:.1f}°C, "
                f"{day['description']}, Humidity: {day['humidity']:.0f}%, "
                f"Rain chance: {day['precipitation_chance']:.0f}%"
                for day in forecast
            ]
        )

        return f"""
You are an agricultural expert advisor. Provide specific, actionable advice for farmers.

Crop Information:
- Crop Name: {crop_name}
- Growth Stage: {growth_stage}

Current Weather Conditions:
- Temperature: {current.get('temperature', 'N/A')}°C
- Feels Like: {current.get('feels_like', 'N/A')}°C
- Humidity: {current.get('humidity', 'N/A')}%
- Conditions: {current.get('description', 'N/A')}
- Wind Speed: {current.get('wind_speed', 'N/A')} m/s
- Location: {current.get('location', 'N/A')}

5-Day Forecast:
{forecast_text}

Based on this information, provide:
1. Assessment of current weather impact on this crop at this growth stage
2. Specific recommendations for the next 5 days
3. Any warnings or precautions needed
4. Irrigation, fertilization, or pest control suggestions if relevant

Keep the advice practical and specific to the weather conditions.
""".strip()

    # Simple chat (stateless, DRF-friendly)
    def chat(self, user_message, conversation_history=None):
        """
        General chatbot function
        conversation_history is accepted for compatibility,
        but Gemini 2.5 works best statelessly for APIs.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_message,
            )
            return response.text

        except Exception as e:
            raise Exception(f"Error in chat: {str(e)}")

    # Chat with agricultural context + history
    def chat_with_context(self, user_message, conversation_history=None):
        agricultural_context = """
You are a helpful agricultural assistant. You help farmers with:
- Crop recommendations and planning
- Weather-related farming advice
- Farming best practices and techniques
- Pest and disease management
- Soil health and fertilization
- Irrigation management

Provide clear, practical, and actionable advice.
""".strip()

        messages = [agricultural_context]

        if conversation_history:
            for msg in conversation_history:
                messages.append(msg["content"])

        messages.append(user_message)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="\n\n".join(messages),
            )
            return response.text

        except Exception as e:
            raise Exception(f"Error in contextual chat: {str(e)}")

    # Image analysis (multimodal)
    def analyze_image(self, image_path, prompt):
        """
        Analyze crop/plant images (disease, pest, stress detection)
        Gemini 2.5 Flash supports multimodal input
        """
        try:
            img = Image.open(image_path)

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, img],
            )
            return response.text

        except Exception as e:
            raise Exception(f"Error analyzing image: {str(e)}")
