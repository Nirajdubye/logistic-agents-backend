import os
import sys
from dotenv import load_dotenv

# Ensure backend directory is in path and env vars are loaded
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.agent.agent import agent
from app.agent.utils import extract_text

THREAD_ID = os.getenv("CHAT_THREAD_ID", "cli-session")


def run_cli_chat():
    print("=" * 60)
    print("  AI Business Operations Assistant CLI")
    print("  Type 'exit' or 'quit' to end session.")
    print("=" * 60)

    while True:
        try:
            question = input("\nYou : ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat.")
            break

        if not question:
            continue

        if question.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        try:
            response = agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": question,
                        }
                    ]
                },
                config={
                    "configurable": {
                        "thread_id": THREAD_ID
                    }
                }
            )

            last_message = response["messages"][-1]
            print("\nAssistant:")
            print(extract_text(last_message))
        except Exception as e:
            print(f"\n[Error executing query]: {e}")


if __name__ == "__main__":
    run_cli_chat()