import os
import time
from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

load_dotenv()

class GeminiClient:
    def __init__(self, model_name: str = "gemini-3.5-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing from environment variables.")
        
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def generate_chat_response(self, history: list, system_instruction: str = None) -> str:
        """Generates a response preserving multi-turn conversation context."""
        config = None
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
            )
            
        # Target Gemini 3 series models
        models_to_try = [self.model_name, "gemini-3.0-flash"]
        
        # Convert history format to GenAI SDK contents structure
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )

        for model in list(dict.fromkeys(models_to_try)):
            for attempt in range(2):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=config,
                    )
                    return response.text
                except APIError as e:
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str:
                        wait = (attempt + 1) * 2
                        print(f"\n⚠️ {model} busy or rate limited. Retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        print(f"\n⚠️ Error on {model}: {e}")
                        break

        raise RuntimeError("Quota exceeded or models unavailable. Please wait a moment.")