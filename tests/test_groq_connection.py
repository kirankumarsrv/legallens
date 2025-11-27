import sys
import os
from dotenv import load_dotenv

# -----------------------------------------
# Ensure project root is in PYTHONPATH
# -----------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT_DIR)

# Load .env
load_dotenv()

from modules.llm_manager import LLMManager


def main():
    print("Initializing Groq LLM...")

    llm = LLMManager(
        provider="groq",
        model_name="llama-3.3-70b-versatile"
    )

    print("Sending test prompt...")

    response = llm.generate("What is 2 + 2? Answer in one word.")

    print("\n===== Groq Response =====")
    print(response)


if __name__ == "__main__":
    main()
