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
You are an agricultural expert advisor.

Crop Information:
- Crop Name: {crop_name}
- Growth Stage: {growth_stage}

Current Weather Conditions:
- Temperature: {current.get('temperature', 'N/A')}°C
- Humidity: {current.get('humidity', 'N/A')}%
- Conditions: {current.get('description', 'N/A')}

Respond ONLY in valid JSON using this exact format:

{{
  "irrigation": {{
    "title": "",
    "description": "",
    "amount": "",
    "timing": "",
    "frequency": ""
  }},
  "fertilization": {{
    "type": "",
    "amount": "",
    "method": "",
    "timing": "",
    "notes": ""
  }},
  "alerts": [
    {{
      "type": "warning",
      "title": "",
      "message": ""
    }}
  ]
}}

Do not include explanations or markdown.
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
You are a helpful agricultural chatbot assistant.

Rules:
- Reply in SHORT conversational answers.
- Do NOT write long essays.
- Keep responses under 120 words.
- Be practical and direct.
- Avoid headings and markdown.
- Talk like a chatbot, not an article writer.

You help farmers with crops, soil, irrigation, fertilizer, pests, and weather.
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
