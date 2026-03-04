import requests
import json

class GeminiService:
    """
    Drop-in replacement using Ollama (llama3.2)
    No changes needed anywhere else in your code
    """

    def __init__(self):
        self.base_url = "http://host.docker.internal:11434/api/generate"
        self.model = "llama3.2"

    # -----------------------------
    # CORE FUNCTION (Ollama call)
    # -----------------------------
    def _generate(self, prompt):
        try:
            response = requests.post(
                self.base_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )

            response.raise_for_status()
            data = response.json()

            return data.get("response", "").strip()

        except Exception as e:
            raise Exception(f"Ollama error: {str(e)}")

    # -----------------------------
    # CROP SUGGESTION
    # -----------------------------
    def get_crop_suggestion(self, crop_name, growth_stage, weather_data):
        prompt = self._create_crop_prompt(crop_name, growth_stage, weather_data)

        response = self._generate(prompt)

        # 🔥 Important: force JSON safety (llama sometimes adds text)
        try:
            return response[response.index("{"):response.rindex("}")+1]
        except:
            raise Exception("Invalid JSON response from model")

    # SAME PROMPT (UNCHANGED)
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

    # -----------------------------
    # SIMPLE CHAT
    # -----------------------------
    def chat(self, user_message, conversation_history=None):
        return self._generate(user_message)

    # -----------------------------
    # CHAT WITH CONTEXT
    # -----------------------------
    def chat_with_context(self, user_message, conversation_history=None):
        agricultural_context = """
You are a helpful agricultural chatbot assistant.

Rules:
- Reply in SHORT conversational answers.
- Keep responses under 120 words.
- Be practical and direct.
- No markdown.
""".strip()

        messages = [agricultural_context]

        if conversation_history:
            for msg in conversation_history:
                messages.append(msg["content"])

        messages.append(user_message)

        prompt = "\n\n".join(messages)

        return self._generate(prompt)

    # -----------------------------
    # IMAGE (NOT SUPPORTED IN LLAMA3.2)
    # -----------------------------
    def analyze_image(self, image_path, prompt):
        raise Exception("Image analysis not supported with llama3.2 in Ollama")
