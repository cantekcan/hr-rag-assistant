"""Information gathering with tool calling.

The model decides which tools to call; our code runs them. The leave tool takes no arguments:
the employee comes from the signed-in session, so the model cannot ask for anyone else's data.
"""
from dataclasses import asdict, dataclass, field
from datetime import date

from google.genai import types

from hr_assistant import config, llm
from hr_assistant.employees import Employee, LeaveBalance, leave_balance
from hr_assistant.retrieval import SearchHit, search

SEARCH_REGULATION = types.FunctionDeclaration(
    name="search_regulation",
    description=("Search the company HR regulation and return matching sections. "
                 "Use a short Turkish query about one topic, for example 'yıllık izin süresi'."),
    parameters_json_schema={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Short Turkish search query."}},
        "required": ["query"],
    },
)

GET_MY_LEAVE_BALANCE = types.FunctionDeclaration(
    name="get_my_leave_balance",
    description=("Get the signed-in employee's own annual leave: years of service, days entitled "
                 "this year, days used and days remaining. Takes no arguments."),
)

GATHER_INSTRUCTIONS = """You collect information for an HR assistant. You do not answer the question yourself.
- Use search_regulation to find the rules that apply. If the question has several topics,
  search each one separately with a short Turkish query.
- Think about what the employee is trying to achieve and also search for other rules that
  could help them, not only the one they named.
- Use get_my_leave_balance only when the question is about the employee's own leave days.
- When you have collected enough, reply with the single word DONE."""


@dataclass
class GatheredFacts:
    hits: list[SearchHit] = field(default_factory=list)
    leave_balance: LeaveBalance | None = None
    tools_used: list[str] = field(default_factory=list)


def _keep_best(best_hits: dict[str, SearchHit], found: list[SearchHit]) -> None:
    for hit in found:
        if hit.section not in best_hits or hit.score > best_hits[hit.section].score:
            best_hits[hit.section] = hit


def gather(question: str, employee: Employee | None, today: date | None = None) -> GatheredFacts:
    tools = [SEARCH_REGULATION] + ([GET_MY_LEAVE_BALANCE] if employee else [])
    contents = [types.Content(role="user", parts=[
        types.Part(text=f"{GATHER_INSTRUCTIONS}\n\nQuestion: {question}")])]
    facts = GatheredFacts()
    best_hits: dict[str, SearchHit] = {}

    for _ in range(config.MAX_TOOL_STEPS):
        response = llm.chat_with_tools(contents, tools)
        calls = response.function_calls or []
        if not calls:
            break
        contents.append(response.candidates[0].content)
        results = []
        for call in calls:
            args = call.args or {}
            if call.name == "search_regulation":
                query = str(args.get("query") or question)
                facts.tools_used.append(f"search_regulation: {query}")
                found = search(query)
                _keep_best(best_hits, found)
                result = {"sections": [{"section": h.section, "text": h.text} for h in found]}
            elif call.name == "get_my_leave_balance" and employee:
                facts.tools_used.append("get_my_leave_balance")
                facts.leave_balance = leave_balance(employee, today or date.today())
                result = asdict(facts.leave_balance)
            else:
                facts.tools_used.append(call.name)
                result = {"error": f"Unknown tool: {call.name}"}
            results.append(types.Part.from_function_response(name=call.name, response=result))
        contents.append(types.Content(role="user", parts=results))

    # Results for the employee's own wording always stay; the model's queries only fill the
    # remaining slots. Retrieval can therefore never be worse than a plain search.
    own_hits = search(question)
    own_sections = {h.section for h in own_hits}
    extra_hits = sorted((h for h in best_hits.values() if h.section not in own_sections),
                        key=lambda h: h.score, reverse=True)
    facts.hits = (own_hits + extra_hits)[:config.MAX_CONTEXT_SECTIONS]
    return facts