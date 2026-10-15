"""Command line chat with the HR assistant.

Run with: python -m hr_assistant.ask
Sign in as a demo employee: python -m hr_assistant.ask --employee E1002
"""
import argparse

from hr_assistant.answer import answer_question
from hr_assistant.employees import Employee, get_employee
from hr_assistant.llm import LLMError


def print_answer(question: str, employee: Employee | None) -> None:
    result = answer_question(question, employee)
    print(f"\n{result.answer}")
    if result.sections:
        print(f"\nKaynak maddeler: {', '.join(result.sections)}")
    if result.tools_used:
        print(f"Kullanılan araçlar: {', '.join(result.tools_used)}")
    if result.model:
        print(f"Yanıtı yazan model: {result.model}")
    print("-" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with the HR assistant.")
    parser.add_argument("--employee", help="Demo employee id to sign in as, e.g. E1002")
    args = parser.parse_args()

    employee = get_employee(args.employee) if args.employee else None
    if args.employee and employee is None:
        parser.error(f"Unknown employee: {args.employee}")

    who = f" ({employee.name} olarak giriş yapıldı)" if employee else ""
    print(f"İK Asistanı{who}. Çıkmak için boş satır bırakıp Enter'a basın.")
    while question := input("\nSoru: ").strip():
        try:
            print_answer(question, employee)
        except LLMError as e:
            print(f"\nDil modeline ulaşılamadı: {e}")


if __name__ == "__main__":
    main()