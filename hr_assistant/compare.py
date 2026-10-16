"""Asks the same question to several answer models and shows what each one wrote.

Information is gathered once, so every model writes from the same regulation sections and
only the writing differs. Nothing falls back to another model: a failure is shown as a failure.

Run with: python -m hr_assistant.compare
Signed in as a demo employee: python -m hr_assistant.compare --employee E1002
All evaluation questions, with a score per model: python -m hr_assistant.compare --eval
"""
import argparse
import json
import time
from dataclasses import dataclass
from functools import partial

from hr_assistant import config, llm
from hr_assistant.answer import AnswerResult, Writer, write_answer
from hr_assistant.employees import Employee, get_employee
from hr_assistant.evaluate import EVAL_DATE, case_employee, score_case
from hr_assistant.llm import LLMError
from hr_assistant.tools import gather

REPORT_PATH = config.PROJECT_ROOT / "eval" / "comparison.md"
EVAL_PAUSE_SECONDS = 20  # Groq's free tier allows few tokens per minute


@dataclass
class Attempt:
    writer: str
    result: AnswerResult | None
    error: str | None
    seconds: float


def writers() -> list[tuple[str, Writer]]:
    groq_writers = [(model, partial(llm.generate_with_groq, model=model)) for model in config.GROQ_MODELS]
    return [*(groq_writers if config.GROQ_API_KEY else []), ("gemini", llm.generate_with_gemini)]


def compare(question: str, employee: Employee | None, today=None) -> list[Attempt]:
    facts = gather(question, employee, today)
    attempts = []
    for name, writer in writers():
        start = time.perf_counter()
        try:
            result, error = write_answer(question, facts, writer), None
        except LLMError as e:
            result, error = None, str(e)
        attempts.append(Attempt(name, result, error, time.perf_counter() - start))
    return attempts


def print_attempts(attempts: list[Attempt]) -> None:
    for a in attempts:
        print(f"\n===== {a.writer} ({a.seconds:.1f} sn) =====")
        if a.error:
            print(f"HATA: {a.error}")
            continue
        print(a.result.answer)
        if a.result.sections:
            print(f"Kaynak maddeler: {', '.join(a.result.sections)}")
        if a.result.model:
            print(f"Yanıtı yazan model: {a.result.model}")


def run_eval() -> None:
    cases = json.loads(config.EVAL_CASES_PATH.read_text(encoding="utf-8"))
    names = [name for name, _ in writers()]
    passed = dict.fromkeys(names, 0)
    report = ["# Model karşılaştırması", "",
              "Her soruda bilgi bir kez toplandı; modeller aynı maddelerden yanıt yazdı.", ""]

    for case in cases:
        print(f"{case['id']} ...")
        try:
            attempts = compare(case["question"], case_employee(case), today=EVAL_DATE)
        except LLMError as e:  # searching failed, so no model could answer this one; keep going
            print(f"  atlandı: {e}")
            report += [f"## {case['id']}", "", f"Atlandı, arama yapılamadı: {e}", ""]
            continue
        report += [f"## {case['id']}", "", f"**Soru:** {case['question']}", ""]
        for a in attempts:
            score = score_case(case, a.result) if a.result else None
            if score and score.passed:
                passed[a.writer] += 1
            verdict = "HATA" if a.error else ("GEÇTİ" if score.passed else f"KALDI ({score.detail})")
            report += [f"### {a.writer}: {verdict}, {a.seconds:.1f} sn", "",
                       a.error or a.result.answer, ""]
        time.sleep(EVAL_PAUSE_SECONDS)

    summary = ["| Model | Doğru |", "|---|---|"] + [f"| {n} | {passed[n]}/{len(cases)} |" for n in names]
    REPORT_PATH.write_text("\n".join(report[:4] + summary + [""] + report[4:]), encoding="utf-8")
    print("\n" + "\n".join(summary))
    print(f"\nTüm yanıtlar: {REPORT_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare answer models on the same question.")
    parser.add_argument("--employee", help="Demo employee id to sign in as, e.g. E1002")
    parser.add_argument("--eval", action="store_true", help="Run every evaluation question")
    args = parser.parse_args()

    if not config.GROQ_API_KEY:
        print("GROQ_API_KEY yok, sadece Gemini çalışacak. Anahtarı .env dosyasına ekleyin.")
    if args.eval:
        run_eval()
        return

    employee = get_employee(args.employee) if args.employee else None
    if args.employee and employee is None:
        parser.error(f"Unknown employee: {args.employee}")
    print("Model karşılaştırması. Çıkmak için boş satır bırakıp Enter'a basın.")
    while question := input("\nSoru: ").strip():
        print_attempts(compare(question, employee))


if __name__ == "__main__":
    main()
