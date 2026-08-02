from dotenv import load_dotenv

from src.agent.controller import create_agent

load_dotenv()


def main():
    print("⚡ AutoCraft Agent Framework Initialized")

    try:
        agent = create_agent()
        response = agent.run(
            "Hello! Verify that the AutoCraft framework setup is complete."
        )
        print("\n🤖 Agent Response:\n", response)

    except Exception as error:
        print(f"\n❌ Setup Check Failed: {error}")


if __name__ == "__main__":
    main()
