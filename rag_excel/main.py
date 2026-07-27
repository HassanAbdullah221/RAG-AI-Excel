# #!/usr/bin/env python3
# """
# main.py
# -------
# Local Retrieval-Augmented Generation (RAG) system over ANY Excel (.xlsx) file,
# running fully offline via Ollama.

# Usage:
#     python main.py <excel_file_path>
#     python main.py                     # will prompt for the path interactively

# Models used (must be pulled beforehand):
#     ollama pull qwen2.5:7b
#     ollama pull nomic-embed-text
# """

# import sys
# import os

# from src.hybrid_pipeline import HybridPipeline
# from src.ollama_client import OllamaError


# def get_excel_path_from_args_or_prompt() -> str:
#     if len(sys.argv) >= 2:
#         return sys.argv[1].strip()

#     print("No Excel file path was provided as an argument.")
#     while True:
#         path = input("Please enter the path to your Excel (.xlsx) file: ").strip().strip('"')
#         if path:
#             return path
#         print("Path cannot be empty. Please try again.")


# def run_chat_loop(pipeline: HybridPipeline) -> None:
#     print("\n" + "=" * 70)
#     print(f"Ready. Ask questions about '{pipeline.file_name}'.")
#     print("Type 'exit', 'quit', or press Ctrl+C to stop.")
#     print("=" * 70 + "\n")

#     while True:
#         try:
#             question = input("Question: ").strip()
#         except (EOFError, KeyboardInterrupt):
#             print("\nGoodbye.")
#             break

#         if not question:
#             continue
#         if question.lower() in {"exit", "quit", "q"}:
#             print("Goodbye.")
#             break

#         try:
#             answer = pipeline.answer(question)
#             print(f"\nAnswer: {answer}\n")
#         except OllamaError as exc:
#             print(f"\n[ERROR] {exc}\n")
#         except Exception as exc:  # noqa: BLE001 - surface any unexpected error to the user
#             print(f"\n[ERROR] Failed to generate an answer: {exc}\n")


# def main() -> int:
#     excel_path = get_excel_path_from_args_or_prompt()

#     if not os.path.isfile(excel_path):
#         print(f"[ERROR] File not found: {excel_path}")
#         return 1

#     try:
#         pipeline = HybridPipeline(excel_path)
#         pipeline.prepare()
#     except OllamaError as exc:
#         print(f"[ERROR] {exc}")
#         return 1
#     except (FileNotFoundError, ValueError) as exc:
#         print(f"[ERROR] {exc}")
#         return 1
#     except Exception as exc:  # noqa: BLE001
#         print(f"[ERROR] Unexpected error while preparing the RAG pipeline: {exc}")
#         return 1

#     run_chat_loop(pipeline)
#     return 0


# if __name__ == "__main__":
#     sys.exit(main())

#!/usr/bin/env python3
"""
main.py
-------
This is the main file that starts the Excel RAG system.

It:
- Gets the Excel file path from the user.
- Creates and prepares the RAG pipeline.
- Starts a chat loop where the user can ask questions about the Excel file.

The system runs locally using Ollama.
"""

import sys
import os

from src.hybrid_pipeline import HybridPipeline
from src.ollama_client import OllamaError


def get_excel_path_from_args_or_prompt() -> str:
    """
    Get the Excel file path.

    The path can come from:
    - a command line argument
    - user input
    """
    if len(sys.argv) >= 2:
        return sys.argv[1].strip()

    print("No Excel file path was provided as an argument.")

    while True:
        path = input(
            "Please enter the path to your Excel (.xlsx) file: "
        ).strip().strip('"')

        if path:
            return path

        print("Path cannot be empty. Please try again.")


def run_chat_loop(pipeline: HybridPipeline) -> None:
    """
    Start the question and answer loop.

    The user can keep asking questions until they type:
    - exit
    - quit
    - q
    """
    print("\n" + "=" * 70)
    print(f"Ready. Ask questions about '{pipeline.file_name}'.")
    print("Type 'exit', 'quit', or press Ctrl+C to stop.")
    print("=" * 70 + "\n")

    while True:
        try:
            question = input("Question: ").strip()

        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        # Ignore empty questions.
        if not question:
            continue

        # Stop the program if the user wants to exit.
        if question.lower() in {"exit", "quit", "q"}:
            print("Goodbye.")
            break

        try:
            answer = pipeline.answer(question)

            print(f"\nAnswer: {answer}\n")

        except OllamaError as exc:
            print(f"\n[ERROR] {exc}\n")

        except Exception as exc:
            print(
                f"\n[ERROR] Failed to generate an answer: {exc}\n"
            )


def main() -> int:
    """
    Main program flow.

    Steps:
    1. Get the Excel file path.
    2. Check that the file exists.
    3. Prepare the RAG pipeline.
    4. Start the chat loop.
    """
    excel_path = get_excel_path_from_args_or_prompt()

    if not os.path.isfile(excel_path):
        print(f"[ERROR] File not found: {excel_path}")
        return 1

    try:
        pipeline = HybridPipeline(excel_path)

        # Load existing data or build new indexes.
        pipeline.prepare()

    except OllamaError as exc:
        print(f"[ERROR] {exc}")
        return 1

    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    except Exception as exc:
        print(
            f"[ERROR] Unexpected error while preparing the RAG pipeline: {exc}"
        )
        return 1

    # Start asking questions.
    run_chat_loop(pipeline)

    return 0


if __name__ == "__main__":
    sys.exit(main())