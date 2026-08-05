import os
import time
from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

from src.security.sandbox import ToolSandbox, create_default_sandbox

load_dotenv()

# Documented stable/fallback models (Aug 2026). Override with GEMINI_MODEL.
_DEFAULT_MODEL = "gemini-3.6-flash"
_FALLBACK_MODELS = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
)


def _is_retryable_api_error(error_str: str) -> bool:
    """Return True when the error indicates a transient condition (rate-limit,
    quota, or temporary unavailability) worth retrying after a back-off."""
    markers = ("429", "RESOURCE_EXHAUSTED", "503")
    return any(m in error_str for m in markers)


class GeminiClient:
    def __init__(
        self,
        model_name: str | None = None,
        sandbox: ToolSandbox | None = None,
    ):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing from environment variables.")

        self.client = genai.Client(api_key=api_key)
        self.model_name = (
            model_name
            or os.getenv("GEMINI_MODEL")
            or _DEFAULT_MODEL
        )

        # All tool calls go through the sandbox allow-list + command policy
        self.sandbox = sandbox if sandbox is not None else create_default_sandbox()
        self.tools = self.sandbox.wrapped_tools()

    def generate_chat_response(self, history: list, system_instruction: str | None = None) -> str:
        """Generates a response with automatic native function/tool execution support."""
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=self.tools,
        ) if system_instruction else types.GenerateContentConfig(tools=self.tools)

        models_to_try = [self.model_name]
        for m in _FALLBACK_MODELS:
            if m != self.model_name:
                models_to_try.append(m)

        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])],
                )
            )

        last_error = None
        for model in models_to_try:
            for attempt in range(2):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=config,
                    )
                    # Guard against empty / tool-only responses
                    text = getattr(response, "text", None)
                    if text is not None and text.strip():
                        return text
                    # Fallback: try to extract from candidates if present
                    if response.candidates:
                        parts = response.candidates[0].content.parts
                        texts = [p.text for p in parts if getattr(p, "text", None)]
                        if texts:
                            return "\n".join(texts)
                    return "(No textual response returned by the model.)"
                except APIError as e:
                    last_error = e
                    err_str = str(e)
                    if _is_retryable_api_error(err_str):
                        wait = (attempt + 1) * 2
                        print(f"\n{model} busy or rate limited. Retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        print(f"\nError on {model}: {e}")
                        break
                except Exception as e:
                    last_error = e
                    print(f"\nUnexpected error on {model}: {e}")
                    break

        raise RuntimeError(
            f"Quota exceeded or models unavailable. Last error: {last_error}"
        )

    def stream_chat_response(
        self, history: list, system_instruction: str | None = None
    ):
        """Yield text chunks from Gemini generate_content_stream when available.

        Falls back to a single full response if streaming is unavailable.
        Tool calling is disabled during streaming for simpler token delivery.
        """
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
        ) if system_instruction else types.GenerateContentConfig()

        models_to_try = [self.model_name]
        for m in _FALLBACK_MODELS:
            if m != self.model_name:
                models_to_try.append(m)

        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])],
                )
            )

        last_error = None
        for model in models_to_try:
            try:
                stream = self.client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=config,
                )
                for chunk in stream:
                    text = getattr(chunk, "text", None)
                    if text:
                        yield text
                return
            except APIError as e:
                last_error = e
                err_str = str(e)
                if _is_retryable_api_error(err_str):
                    wait = 2
                    print(f"\n{model} busy during stream. Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"\nStream error on {model}: {e}")
                break
            except Exception as e:
                last_error = e
                print(f"\nUnexpected stream error on {model}: {e}")
                break

        # Fallback: non-streaming full response as one chunk
        try:
            full = self.generate_chat_response(history, system_instruction)
            if full:
                yield full
        except Exception as e:
            raise RuntimeError(
                f"Streaming failed and fallback failed. Last error: {last_error}; fallback: {e}"
            ) from e
