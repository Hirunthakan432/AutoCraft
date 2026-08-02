from src.agent.controller import AgentController, create_agent, DEFAULT_SYSTEM


def run_cli(use_mock: bool = False):
    print("=" * 60)
    print("🤖 AutoCraft Interactive CLI")
    print("Type 'exit' or 'quit' to end session.")
    print("Type '/clear' to reset chat memory.")
    print("=" * 60 + "\n")

    agent: AgentController = create_agent(
        use_mock=use_mock,
        system_instruction=DEFAULT_SYSTEM,
    )

    while True:
        try:
            user_input = input("You > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                print("👋 Shutting down AutoCraft session. Goodbye!")
                break

            if user_input.lower() == "/clear":
                agent.clear_session()
                print("🧹 Conversation memory cleared.\n")
                continue

            print("\nAutoCraft > ", end="", flush=True)
            response = agent.chat(user_input)
            print(response + "\n")

        except KeyboardInterrupt:
            print("\n👋 Session interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    run_cli()
