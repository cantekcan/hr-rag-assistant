"""Command line chat with the HR assistant.

Run with: python -m hr_assistant.ask
Or ask a single question: python -m hr_assistant.ask "Deneme süresi ne kadar?"
"""
import sys

from hr_assistant.answer import answer_question


def print_answer(question: str) -> None:
    result = answer_question(question)
    print(f"\n{result.answer}")
    if result.sections:
        print(f"\nKaynak maddeler: {', '.join(result.sections)}")
    print("-" * 60)


def main() -> None:
    if len(sys.argv) > 1:
        print_answer(" ".join(sys.argv[1:]))
        return

    print("İK Asistanı. Çıkmak için boş satır bırakıp Enter'a basın.")
    while question := input("\nSoru: ").strip():
        print_answer(question)


if __name__ == "__main__":
    main()