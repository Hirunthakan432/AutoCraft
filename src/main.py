import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

def main():
    print("⚡ AutoCraft Agent Framework Initialized")
    
    # Quick sanity check for keys
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if openai_key or gemini_key:
        print("✅ Environment variables loaded successfully!")
    else:
        print("⚠️ Warning: No API keys found in .env file.")

if __name__ == "__main__":
    main()