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

    def generate_response(self, prompt: str, system_instruction: str = None) -> str:
        """Generates a response using Gemini 3.5 Flash with fallback logic."""
        config = None
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
            )
            
        # Fallback cascade
        models_to_try = [self.model_name, "gemini-3.0-flash", "gemini-2.5-flash"]
        
        for model in list(dict.fromkeys(models_to_try)):
            for attempt in range(2):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config,
                    )
                    return response.text
                except APIError as e:
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str:
                        wait = (attempt + 1) * 3
                        print(f"⚠️ {model} high demand / rate limit. Retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        print(f"⚠️ Model {model} unavailable: {e}")
                        break
                        
            print(f"🔄 Switching to fallback model...")

        raise RuntimeError("All configured Gemini models are currently busy or rate-limited.")

if __name__ == "__main__":
    ai = GeminiClient()
    reply = ai.generate_response(
        prompt="Write a 1-sentence tagline for AutoCraft.",
        system_instruction="You are an expert AI software architect."
    )
    print("🤖 Gemini Response:\n", reply)