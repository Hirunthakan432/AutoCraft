from dotenv import load_dotenv
from src.core.llm import GeminiClient

load_dotenv()


def main():
    print("⚡ AutoCraft Agent Framework Initialized (Gemini Powered)")

    try:
        ai = GeminiClient()

        response = ai.generate_chat_response(
            history=[
                {
                    "role": "user",
                    "content": "Hello! Verify that the AutoCraft framework setup is complete."
                }
            ],
            system_instruction="You are AutoCraft, an intelligent AI software agent for automated development workflows."
        )

        print("\n🤖 Gemini Agent Response:\n", response)

    except Exception as error:
        print(f"\n❌ Setup Check Failed: {error}")


if __name__ == "__main__":
    main()
