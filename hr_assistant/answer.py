"""Turns a question into a grounded answer: gather facts, structured answer, validation, routing."""
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from hr_assistant import llm
from hr_assistant.employees import Employee, LeaveBalance
from hr_assistant.retrieval import RegulationSection, SearchHit, get_sections
from hr_assistant.tools import GatheredFacts, gather

logger = logging.getLogger(__name__)

NO_ANSWER_TEXT = "Bu konuda bilgim yok. Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz."
MISSING_INFO_TEXT = ("Yönetmelikte şu konularda bilgi bulunmuyor: {items}. "
                     "Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.")
HELP_TEXT = ("Merhaba! Şirketin İnsan Kaynakları Yönetmeliği hakkındaki sorularınızı yanıtlayabilirim. "
             "Örneğin yıllık izin, mazeret ve doğum izinleri, çalışma saatleri, deneme süresi veya "
             "disiplin süreçleri hakkında sorabilirsiniz. Giriş yaptıysanız kalan izin günlerinizi de sorabilirsiniz.")
THANKS_TEXT = "Rica ederim! Başka bir sorunuz olursa yardımcı olmaktan memnuniyet duyarım."


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    sections: list[str] = field(default_factory=list)
    refused: bool = False  # True when the answer is not based on the document
    missing_info: list[str] = field(default_factory=list)
    # The "not covered" sentence already appended to `answer`, so a UI can show it separately
    missing_info_note: str | None = None
    tools_used: list[str] = field(default_factory=list)
    sources: list[RegulationSection] = field(default_factory=list)  # text of the cited sections
    model: str | None = None  # model that wrote the answer; None for fixed replies


class HRAnswer(BaseModel):
    can_answer: bool = Field(description="False only if no part of the question can be answered from the excerpts.")
    answer: str = Field(description="Answer in Turkish, addressed to the employee. No section numbers.")
    used_sections: list[str] = Field(description="Section numbers of the excerpts actually used in the answer.")
    used_leave_record: bool = Field(description="True if the answer uses the employee leave record.")
    missing_info: list[str] = Field(description="Parts of the question the excerpts do not cover, as short Turkish phrases.")


class MessageIntent(BaseModel):
    intent: Literal["hr_question", "greeting_or_help", "thanks_or_goodbye", "other"]


ANSWER_INSTRUCTIONS = """You are an HR assistant for the employees of a company.
You answer questions using only the regulation excerpts given below.

How to read the excerpts:
- Each excerpt has a section number, a section path and the section text.
- The section path only shows where the section sits in the document. Section titles can be
  imprecise, so take the rule, who it applies to and its conditions from the section text itself.
- Some excerpts may be unrelated to the question. Use only the ones that answer it and
  ignore the others without mentioning them.
- An employee leave record may be given. It is calculated from the regulation for the
  employee asking; use its numbers when they ask about their own leave.

How to answer:
- Find every separate thing the person is asking and answer each of them.
- Consider everyone the question is about: the employee and anyone they mention.
  Include every right in the excerpts that applies to their situation.
- Do not add rules for situations or people the question does not mention.
- Never guess, never use outside knowledge (for example general labour law) and never
  calculate amounts the excerpts do not state. Put such parts in missing_info instead.
- Set can_answer to false only if no part of the question can be answered from the excerpts.
- Write the answer in clear, plain Turkish. Do not put section numbers in the answer text."""

ROUTER_INSTRUCTIONS = """Classify the user's message sent to a company HR assistant.
- hr_question: asks about work rules, leave, working hours, pay, benefits, discipline or other employment matters.
- greeting_or_help: greetings, or asking what the assistant can do.
- thanks_or_goodbye: thanking the assistant or ending the conversation.
- other: anything else."""

ROUTED_REPLIES = {"greeting_or_help": HELP_TEXT, "thanks_or_goodbye": THANKS_TEXT}


def _format_context(hits: list[SearchHit], balance: LeaveBalance | None) -> str:
    blocks = [f"[Section {h.section}]\nPath: {h.path or '-'}\nText: {h.text}" for h in hits]
    if balance:
        blocks.append(
            f"[Employee leave record, based on section {balance.rule_section}]\n"
            f"Employee: {balance.employee_name}, started {balance.start_date}, "
            f"{balance.years_of_service} completed years of service\n"
            f"Entitled to annual leave yet: {'yes' if balance.eligible else 'no'}\n"
            f"Entitled days this year: {balance.entitled_days}, used: {balance.used_days}, "
            f"remaining: {balance.remaining_days}")
    return "\n\n".join(blocks)


def _refusal(question: str, tools_used: list[str]) -> AnswerResult:
    # Only called when we are about to refuse, so normal HR questions cost no extra request
    routed = llm.generate(f"{ROUTER_INSTRUCTIONS}\n\nMessage: {question}", schema=MessageIntent)
    return AnswerResult(answer=ROUTED_REPLIES.get(routed.intent, NO_ANSWER_TEXT),
                        refused=True, tools_used=tools_used)


# Writes the structured answer from a prompt; returns it with the name of the model that wrote it
Writer = Callable[[str, type[HRAnswer]], tuple[HRAnswer, str]]


def answer_question(question: str, employee: Employee | None = None,
                    today: date | None = None) -> AnswerResult:
    return write_answer(question, gather(question, employee, today))


def write_answer(question: str, facts: GatheredFacts, writer: Writer | None = None) -> AnswerResult:
    """The answer step on its own, so several models can write from the same gathered facts."""
    if not facts.hits and not facts.leave_balance:
        return _refusal(question, facts.tools_used)

    context = _format_context(facts.hits, facts.leave_balance)
    prompt = f"{ANSWER_INSTRUCTIONS}\n\nExcerpts:\n{context}\n\nQuestion: {question}"
    result, model = (writer or llm.generate_with_model)(prompt, HRAnswer)
    if not result.can_answer:
        return _refusal(question, facts.tools_used)

    answer = result.answer.strip()
    note = None
    if result.missing_info:
        # Kept inside the answer text too, so a client that ignores missing_info still shows it
        note = MISSING_INFO_TEXT.format(items=", ".join(result.missing_info))
        answer += "\n\n" + note

    retrieved = {h.section: h for h in facts.hits}
    sections = [s for s in result.used_sections if s in retrieved]  # drop invented section numbers
    if result.used_leave_record and facts.leave_balance and facts.leave_balance.rule_section not in sections:
        sections.append(facts.leave_balance.rule_section)  # the record cites its rule, added by code
    return AnswerResult(answer=answer, sections=sections, missing_info=result.missing_info,
                        missing_info_note=note, tools_used=facts.tools_used,
                        sources=_sources(sections, retrieved), model=model)


def _sources(sections: list[str], retrieved: dict[str, SearchHit]) -> list[RegulationSection]:
    # Use the text the model actually saw; only sections added by code (the leave rule) need a lookup
    looked_up: dict[str, RegulationSection] = {}
    not_retrieved = [s for s in sections if s not in retrieved]
    if not_retrieved:
        try:
            looked_up = {r.section: r for r in get_sections(not_retrieved)}
        except Exception:  # the answer is already generated; a missing source text must not lose it
            logger.exception("Could not load section text for %s", not_retrieved)

    sources = []
    for number in sections:
        if hit := retrieved.get(number):
            sources.append(RegulationSection(section=hit.section, page=hit.page, path=hit.path, text=hit.text))
        elif number in looked_up:
            sources.append(looked_up[number])
    return sources
