import sys
from src.core.llm import GeminiClient
from src.core.memory import ConversationMemory

SYSTEM_PROMPT = """You are AutoCraft, an intelligent AI software architecture & automation agent. 
You provide concise, high-quality, and structured technical responses."""

def run_cli():
    print("=" * 60)
    print("🤖 AutoCraft Interactive CLI")
    print("Type 'exit' or 'quit' to end session.")
    print("Type '/clear' to reset chat memory.")
    print("=" * 60 + "\n")

    ai = GeminiClient()
    memory = ConversationMemory(system_instruction=SYSTEM_PROMPT)

    while True:
        try:
            user_input = input("You > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                print("👋 Shutting down AutoCraft session. Goodbye!")
                break

            if user_input.lower() == "/clear":
                memory.clear()
                print("🧹 Conversation memory cleared.\n")
                continue

            memory.add_user_message(user_input)
            
            print("\nAutoCraft > ", end="", flush=True)
            response = ai.generate_chat_response(
                history=memory.get_history(),
                system_instruction=memory.system_instruction
            )
            print(response + "\n")
            
            memory.add_agent_message(response)

        except KeyboardInterrupt:
            print("\n👋 Session interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    run_cli()