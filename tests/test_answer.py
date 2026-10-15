"""Code-side decisions in answer_question, with information gathering and the model replaced by fakes."""
from datetime import date

import pytest

from hr_assistant import answer
from hr_assistant.answer import MISSING_INFO_TEXT, HRAnswer, answer_question
from hr_assistant.employees import LeaveBalance
from hr_assistant.retrieval import RegulationSection, SearchHit
from hr_assistant.tools import GatheredFacts

HIT = SearchHit(section="5.7.5.1.1", page=8, path="5.7.5. Mazeret izni", text="5.7.5.1.1. Evlenmesi ... üç gün,", score=0.8)
BALANCE = LeaveBalance(employee_name="Test", start_date="2016-06-15", years_of_service=10, eligible=True,
                       entitled_days=20, used_days=12, remaining_days=8, rule_section="5.7.4.2")
RULE = RegulationSection(section="5.7.4.2", page=7, path="5.7.4. Yıllık izin", text="5.7.4.2. ... yirmi iş günü,")


@pytest.fixture
def run(monkeypatch):
    def install(model_answer: HRAnswer, facts: GatheredFacts, lookup=None):
        monkeypatch.setattr(answer, "gather", lambda question, employee, today: facts)
        monkeypatch.setattr(answer.llm, "generate_with_model", lambda prompt, schema: (model_answer, "test-model"))
        monkeypatch.setattr(answer, "get_sections", lookup or (lambda numbers: []))
        return answer_question("soru", today=date(2026, 10, 15))
    return install


def model(**overrides) -> HRAnswer:
    values = dict(can_answer=True, answer="Üç gün izin alırsınız.", used_sections=[],
                  used_leave_record=False, missing_info=[])
    return HRAnswer(**(values | overrides))


def test_uncovered_part_stays_in_the_answer_text(run):
    result = run(model(missing_info=["tazminat hesabı"]), GatheredFacts(hits=[HIT]))
    note = MISSING_INFO_TEXT.format(items="tazminat hesabı")
    assert result.missing_info_note == note
    assert result.answer.endswith(note)  # clients that ignore missing_info still see it
    assert result.model == "test-model"


def test_invented_sections_are_dropped_and_sources_use_retrieved_text(run):
    result = run(model(used_sections=["5.7.5.1.1", "9.9.9"]), GatheredFacts(hits=[HIT]))
    assert result.sections == ["5.7.5.1.1"]
    assert result.sources[0].text == HIT.text


def test_leave_rule_section_is_looked_up(run):
    facts = GatheredFacts(hits=[HIT], leave_balance=BALANCE)
    result = run(model(used_leave_record=True), facts, lookup=lambda numbers: [RULE])
    assert result.sections == ["5.7.4.2"]
    assert result.sources == [RULE]


def test_failed_lookup_keeps_the_answer(run):
    def broken(numbers):
        raise RuntimeError("vector store unavailable")
    facts = GatheredFacts(hits=[HIT], leave_balance=BALANCE)
    result = run(model(used_leave_record=True), facts, lookup=broken)
    assert result.answer == "Üç gün izin alırsınız."
    assert result.sections == ["5.7.4.2"]  # still cited, only its text is missing
    assert result.sources == []
