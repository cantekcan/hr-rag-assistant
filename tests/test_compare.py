"""Model comparison: facts gathered once, every model writes, failures are shown and not replaced."""
from types import SimpleNamespace

import groq
import httpx
import pytest

from hr_assistant import compare, llm
from hr_assistant.answer import HRAnswer
from hr_assistant.llm import LLMError
from hr_assistant.retrieval import SearchHit
from hr_assistant.tools import GatheredFacts

HIT = SearchHit(section="5.5.7", page=6, path="5.5. Haklar", text="5.5.7. Şikayet ... amirler atlanarak yapılır.", score=0.8)


def model_answer(text: str) -> HRAnswer:
    return HRAnswer(can_answer=True, answer=text, used_sections=["5.5.7"], used_leave_record=False, missing_info=[])


def test_every_model_writes_from_the_same_facts(monkeypatch):
    gathered = []
    monkeypatch.setattr(compare, "gather", lambda q, e, t: gathered.append(q) or GatheredFacts(hits=[HIT]))

    def failing(prompt, schema):
        raise LLMError("quota")

    monkeypatch.setattr(compare, "writers", lambda: [
        ("qwen", lambda prompt, schema: (model_answer("atlanarak"), "groq/qwen")),
        ("oss", failing),
        ("gemini", lambda prompt, schema: (model_answer("atlanmadan"), "gemini-flash")),
    ])
    attempts = compare.compare("Amirim bana küfür etti", None)

    assert gathered == ["Amirim bana küfür etti"]  # searched once for all models
    assert [a.writer for a in attempts] == ["qwen", "oss", "gemini"]
    assert attempts[0].result.answer == "atlanarak" and attempts[0].result.model == "groq/qwen"
    assert attempts[1].result is None and attempts[1].error == "quota"  # no silent fallback
    assert attempts[2].result.sections == ["5.5.7"]


def test_without_groq_key_only_gemini_is_compared(monkeypatch):
    monkeypatch.setattr(compare.config, "GROQ_API_KEY", None)
    assert [name for name, _ in compare.writers()] == ["gemini"]


def test_groq_models_come_first(monkeypatch):
    monkeypatch.setattr(compare.config, "GROQ_API_KEY", "gsk_test")
    monkeypatch.setattr(compare.config, "GROQ_MODELS", ["qwen-test", "oss-test"])
    assert [name for name, _ in compare.writers()] == ["qwen-test", "oss-test", "gemini"]


def groq_client(content=None, error=None, requests=None):
    def create(**kwargs):
        if requests is not None:
            requests.append(kwargs)
        if error:
            raise error
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                               model=kwargs["model"])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_groq_answer_and_model_name(monkeypatch):
    content = model_answer("Üç gün.").model_dump_json()
    monkeypatch.setattr(llm, "_groq_client", lambda: groq_client(content))
    answer, model = llm.generate_with_groq("soru", HRAnswer, model="qwen-test")
    assert answer.answer == "Üç gün."
    assert model == "groq/qwen-test"


def test_json_mode_models_get_the_schema_in_the_prompt(monkeypatch):
    requests = []
    monkeypatch.setattr(llm, "_groq_client", lambda: groq_client(model_answer("Üç gün.").model_dump_json(), requests=requests))
    monkeypatch.setattr(llm.config, "GROQ_JSON_MODE_MODELS", {"qwen-test"})

    llm.generate_with_groq("soru", HRAnswer, model="qwen-test")
    llm.generate_with_groq("soru", HRAnswer, model="oss-test")

    qwen, oss = requests
    assert qwen["response_format"] == {"type": "json_object"}
    assert qwen["messages"][0]["role"] == "system" and "used_sections" in qwen["messages"][0]["content"]
    assert oss["response_format"]["json_schema"]["strict"] is True
    assert len(oss["messages"]) == 1


@pytest.mark.parametrize("client", [
    groq_client(error=groq.APIConnectionError(request=httpx.Request("POST", "https://api.groq.com"))),
    groq_client("not json"),
])
def test_groq_failure_is_an_llm_error(monkeypatch, client):
    monkeypatch.setattr(llm, "_groq_client", lambda: client)
    with pytest.raises(LLMError):
        llm.generate_with_groq("soru", HRAnswer, model="qwen-test")


def test_strict_schema_requires_every_field_and_allows_no_others():
    schema = llm.strict_json_schema(HRAnswer)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(HRAnswer.model_fields)


@pytest.fixture
def answer_chain(monkeypatch):
    """The app's answer models: Groq models in order, then Gemini. Returns the list of models asked."""
    def install(failing):
        asked = []

        def groq_writer(prompt, schema, model):
            asked.append(model)
            if model in failing:
                raise LLMError(f"{model} failed")
            return model_answer("Tamam."), f"groq/{model}"

        def gemini_writer(prompt, schema):
            asked.append("gemini")
            return model_answer("Tamam."), "gemini-test"

        monkeypatch.setattr(llm.config, "GROQ_API_KEY", "gsk_test")
        monkeypatch.setattr(llm.config, "GROQ_MODELS", ["qwen-test", "oss-test"])
        monkeypatch.setattr(llm, "generate_with_groq", groq_writer)
        monkeypatch.setattr(llm, "generate_with_gemini", gemini_writer)
        return asked
    return install


def test_first_groq_model_answers(answer_chain):
    asked = answer_chain(failing=set())
    assert llm.generate_with_model("soru", HRAnswer)[1] == "groq/qwen-test"
    assert asked == ["qwen-test"]


def test_next_groq_model_answers_when_the_first_fails(answer_chain):
    asked = answer_chain(failing={"qwen-test"})
    assert llm.generate_with_model("soru", HRAnswer)[1] == "groq/oss-test"
    assert asked == ["qwen-test", "oss-test"]


def test_gemini_answers_when_every_groq_model_fails(answer_chain):
    asked = answer_chain(failing={"qwen-test", "oss-test"})
    assert llm.generate_with_model("soru", HRAnswer)[1] == "gemini-test"
    assert asked == ["qwen-test", "oss-test", "gemini"]


def test_without_groq_key_gemini_answers(answer_chain, monkeypatch):
    asked = answer_chain(failing=set())
    monkeypatch.setattr(llm.config, "GROQ_API_KEY", None)
    assert llm.generate_with_model("soru", HRAnswer)[1] == "gemini-test"
    assert asked == ["gemini"]
