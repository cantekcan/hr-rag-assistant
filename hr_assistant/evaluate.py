"""Runs the evaluation set and prints a score.

Run with: python -m hr_assistant.evaluate
"""
import json
import re
import time
from dataclasses import dataclass
from datetime import date

from hr_assistant import config
from hr_assistant.answer import answer_question
from hr_assistant.employees import get_employee

SECTION_NUMBER = re.compile(r"\d+(?:\.\d+)+")
PAUSE_SECONDS = 4  # stay under the free tier request limit
EVAL_DATE = date(2026, 10, 15)  # fixed so leave balances in the test cases do not change over time


@dataclass(frozen=True)
class CaseResult:
    id: str
    passed: bool
    # Share of expected sections the answer cites; None for questions the document does not cover
    citation_recall: float | None
    detail: str


def normalize(text: str) -> str:
    # Turkish-aware lowercase: "İ" -> "i", "I" -> "ı"
    return text.replace("İ", "i").replace("I", "ı").lower()


def contains_keyword(answer: str, keyword: str) -> bool:
    # Section numbers like 5.7.5.1.3 must not count as matches for "3"
    text = SECTION_NUMBER.sub(" ", answer)
    # Starts at a word boundary; Turkish suffixes may follow ("2 aydır") but not more digits ("140")
    pattern = rf"(?<![\w,]){re.escape(normalize(keyword))}(?!,?\d)"
    return re.search(pattern, text) is not None


def evaluate_case(case: dict) -> CaseResult:
    employee = get_employee(case["employee_id"]) if "employee_id" in case else None
    result = answer_question(case["question"], employee, today=EVAL_DATE)
    answer = normalize(result.answer)

    if case.get("expect_no_answer"):
        # Refusing, or answering while flagging the missing part, are both fine. Pretending to know is not.
        passed = result.refused or bool(result.missing_info)
        detail = "refused" if result.refused else "flagged as not covered"
        return CaseResult(case["id"], passed, None,
                          detail if passed else "answered as if the document covered it")

    expected = case["expected_sections"]
    citation_recall = len([s for s in expected if s in result.sections]) / len(expected)
    if result.refused:
        return CaseResult(case["id"], False, citation_recall, "refused but answer exists")

    missing = [group for group in case["expected_keywords"]
               if not any(contains_keyword(answer, word) for word in group)]
    unwanted = [word for word in case.get("forbidden_keywords", []) if normalize(word) in answer]

    problems = []
    if missing:
        problems.append(f"missing: {missing}")
    if unwanted:
        problems.append(f"unwanted: {unwanted}")
    if case.get("expect_missing_info") and not result.missing_info:
        # Part of the question is not in the document and must be flagged, not answered
        problems.append("uncovered part not flagged")
    return CaseResult(case["id"], not problems, citation_recall, "; ".join(problems) or "ok")


def main() -> None:
    cases = json.loads(config.EVAL_CASES_PATH.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        r = evaluate_case(case)
        results.append(r)
        recall = "-" if r.citation_recall is None else f"{r.citation_recall:.0%}"
        print(f"[{'PASS' if r.passed else 'FAIL'}] {r.id:<32} citations: {recall:<5} {r.detail}")
        time.sleep(PAUSE_SECONDS)

    passed = sum(r.passed for r in results)
    scored = [r.citation_recall for r in results if r.citation_recall is not None]
    print("-" * 72)
    print(f"Answers correct: {passed}/{len(results)}")
    if scored:
        print(f"Average citation recall: {sum(scored) / len(scored):.0%}")


if __name__ == "__main__":
    main()
