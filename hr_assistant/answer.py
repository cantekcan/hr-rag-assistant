"""Turns a question into a grounded answer: search, prompt, structured output, routing."""
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from hr_assistant import llm
from hr_assistant.retrieval import SearchHit, search

NO_ANSWER_TEXT = "Bu konuda bilgim yok. Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz."
MISSING_INFO_TEXT = ("Yönetmelikte şu konularda bilgi bulunmuyor: {items}. "
                     "Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.")
HELP_TEXT = ("Merhaba! Şirketin İnsan Kaynakları Yönetmeliği hakkındaki sorularınızı yanıtlayabilirim. "
             "Örneğin yıllık izin, mazeret ve doğum izinleri, çalışma saatleri, deneme süresi veya "
             "disiplin süreçleri hakkında sorabilirsiniz.")
THANKS_TEXT = "Rica ederim! Başka bir sorunuz olursa yardımcı olmaktan memnuniyet duyarım."


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    sections: list[str] = field(default_factory=list)
    refused: bool = False  # True when the answer is not based on the document
    missing_info: list[str] = field(default_factory=list)


class HRAnswer(BaseModel):
    can_answer: bool = Field(description="False only if no part of the question can be answered from the excerpts.")
    answer: str = Field(description="Answer in Turkish, addressed to the employee. No section numbers.")
    used_sections: list[str] = Field(description="Section numbers of the excerpts actually used in the answer.")
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


def _format_context(hits: list[SearchHit]) -> str:
    return "\n\n".join(
        f"[Section {h.section}]\nPath: {h.path or '-'}\nText: {h.text}" for h in hits)


def _refusal(question: str) -> AnswerResult:
    # Only called when we are about to refuse, so normal HR questions cost no extra request
    routed = llm.generate(f"{ROUTER_INSTRUCTIONS}\n\nMessage: {question}", schema=MessageIntent)
    return AnswerResult(answer=ROUTED_REPLIES.get(routed.intent, NO_ANSWER_TEXT), refused=True)


def answer_question(question: str) -> AnswerResult:
    hits = search(question)
    if not hits:
        return _refusal(question)

    prompt = f"{ANSWER_INSTRUCTIONS}\n\nExcerpts:\n{_format_context(hits)}\n\nQuestion: {question}"
    result = llm.generate(prompt, schema=HRAnswer)
    if not result.can_answer:
        return _refusal(question)

    answer = result.answer.strip()
    if result.missing_info:
        answer += "\n\n" + MISSING_INFO_TEXT.format(items=", ".join(result.missing_info))

    retrieved = {h.section for h in hits}
    sections = [s for s in result.used_sections if s in retrieved]  # drop invented section numbers
    return AnswerResult(answer=answer, sections=sections, missing_info=result.missing_info)