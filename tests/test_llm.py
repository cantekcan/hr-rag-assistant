"""Retry and fallback behaviour, with the Gemini client replaced by a fake."""
from types import SimpleNamespace

import pytest
from google.genai import errors, types

from hr_assistant import config, llm
from hr_assistant.answer import MessageIntent


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)  # one per call: an exception to raise or a response to return
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def fake(monkeypatch):
    def install(*outcomes):
        models = FakeModels(outcomes)
        monkeypatch.setattr(llm, "_client", lambda: SimpleNamespace(models=models))
        monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)
        monkeypatch.setattr(config, "GENERATION_MODELS", ["first", "second"])
        return models
    return install


def api_error(code: int) -> errors.APIError:
    return errors.APIError(code, {"error": {"message": "test"}})


def response(text: str | None = "{}", model_version: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(candidates=[object()], parsed=None, text=text, model_version=model_version)


CONFIG = types.GenerateContentConfig()


def test_falls_back_to_next_model_on_temporary_error(fake):
    models = fake(api_error(503), response())
    llm._generate_with_fallback("q", CONFIG)
    assert models.calls == ["first", "second"]


@pytest.mark.parametrize("code", [400, 401, 403])
def test_permanent_error_fails_without_retry(fake, code):
    models = fake(api_error(code))
    with pytest.raises(llm.LLMError):
        llm._generate_with_fallback("q", CONFIG)
    assert models.calls == ["first"]


def test_gives_up_after_all_rounds(fake):
    models = fake(*[api_error(429)] * 6)
    with pytest.raises(llm.LLMError):
        llm._generate_with_fallback("q", CONFIG, rounds=3)
    assert len(models.calls) == 6


def test_blocked_response_is_an_error(fake):
    fake(SimpleNamespace(candidates=[], parsed=None, text=None))
    with pytest.raises(llm.LLMError):
        llm._generate_with_fallback("q", CONFIG)


def test_unparseable_answer_is_an_error(fake):
    fake(response(text="not json"))
    with pytest.raises(llm.LLMError):
        llm.generate("q", schema=MessageIntent)


def test_reports_the_model_that_answered(fake):
    answered = response(text='{"intent": "other"}')
    fake(api_error(503), answered)
    _, model = llm.generate_with_model("q", schema=MessageIntent)
    assert model == "second"  # the fallback model, not the first one in the list
    assert answered.model_version is None  # the SDK response is left as it came


def test_reports_the_resolved_version_when_the_api_gives_it(fake):
    fake(response(text='{"intent": "other"}', model_version="gemini-2.5-flash-lite"))
    _, model = llm.generate_with_model("q", schema=MessageIntent)
    assert model == "gemini-2.5-flash-lite"
