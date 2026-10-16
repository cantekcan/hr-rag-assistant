"""Model access: Gemini for embeddings and tool calling; Groq models first, then Gemini, for answers."""
import json
import logging
import time
from collections.abc import Callable
from functools import cache
from typing import TypeVar

import groq
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from hr_assistant import config

logger = logging.getLogger(__name__)

T = TypeVar("T")
SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMError(RuntimeError):
    """The model could not produce a usable response."""


@cache
def _client() -> genai.Client:
    if not config.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY is not set. Add it to the .env file.")
    return genai.Client(api_key=config.GEMINI_API_KEY)


@cache
def _groq_client() -> groq.Groq:
    if not config.GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY is not set. Add it to the .env file.")
    return groq.Groq(api_key=config.GROQ_API_KEY, max_retries=0, timeout=60)


def _is_temporary(error: errors.APIError) -> bool:
    # Quota and server errors pass; 404 means this model is gone, another one may still work.
    # Anything else (bad request, invalid key) fails the same way on every retry.
    return error.code in (404, 429) or error.code >= 500


def _with_retry(operation: Callable[[], T], max_attempts: int = 5) -> T:
    for attempt in range(max_attempts):
        try:
            return operation()
        except errors.APIError as e:
            if not _is_temporary(e) or attempt == max_attempts - 1:
                raise LLMError(f"Embedding request failed ({e.code}).") from e
            wait = 60 if e.code == 429 else 2 ** attempt
            logger.warning("Embedding request failed (%s), retrying in %s seconds", e.code, wait)
            time.sleep(wait)
    raise AssertionError("unreachable")


def embed(texts: list[str]) -> list[list[float]]:
    result = _with_retry(lambda: _client().models.embed_content(
        model=config.EMBEDDING_MODEL, contents=texts))
    return [e.values for e in result.embeddings]


def _generate_with_fallback(contents: str | list[types.Content],
                            generation_config: types.GenerateContentConfig,
                            rounds: int = 3) -> tuple[types.GenerateContentResponse, str]:
    """The first usable response, with the model version that produced it."""
    for r in range(rounds):
        for model in config.GENERATION_MODELS:
            try:
                response = _client().models.generate_content(
                    model=model, contents=contents, config=generation_config)
            except errors.APIError as e:
                if not _is_temporary(e):
                    raise LLMError(f"{model} rejected the request ({e.code}).") from e
                logger.warning("%s unavailable (%s)", model, e.code)
                continue
            if not response.candidates:  # e.g. blocked by a safety filter
                raise LLMError(f"{model} returned no answer.")
            # The API reports the resolved version behind an alias; fall back to the name we asked for
            return response, response.model_version or model
        if r < rounds - 1:
            wait = 5 * (r + 1)
            logger.warning("All models busy, retrying in %s seconds", wait)
            time.sleep(wait)
    raise LLMError("No model responded, try again in a few minutes.")


def generate(prompt: str, schema: type[SchemaT]) -> SchemaT:
    """Ask the model for JSON matching `schema` and return it as a typed object."""
    return generate_with_model(prompt, schema)[0]


def generate_with_model(prompt: str, schema: type[SchemaT]) -> tuple[SchemaT, str]:
    """Like generate, and also returns the model that answered: the Groq models in order, then Gemini."""
    if config.GROQ_API_KEY:
        for model in config.GROQ_MODELS:
            try:
                return generate_with_groq(prompt, schema, model)
            except LLMError as e:  # quota, server error or bad output: the next model takes over
                logger.warning("%s", e)
    return generate_with_gemini(prompt, schema)


def generate_with_gemini(prompt: str, schema: type[SchemaT]) -> tuple[SchemaT, str]:
    """Gemini only, with its own retry and model fallback."""
    response, model = _generate_with_fallback(prompt, types.GenerateContentConfig(
        temperature=0,  # consistent answers for the same question
        response_mime_type="application/json",
        response_schema=schema,
    ))
    if isinstance(response.parsed, schema):
        return response.parsed, model
    try:
        return schema.model_validate_json(response.text or ""), model
    except ValidationError as e:
        raise LLMError("The model's answer did not match the expected format.") from e


def strict_json_schema(schema: type[BaseModel]) -> dict:
    """JSON schema for Groq's strict mode: every object lists all its properties as required and allows no others."""
    json_schema = schema.model_json_schema()

    def close(node: object) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for value in node.values():
                close(value)
        elif isinstance(node, list):
            for item in node:
                close(item)

    close(json_schema)
    return json_schema


def generate_with_groq(prompt: str, schema: type[SchemaT], model: str) -> tuple[SchemaT, str]:
    """One Groq model and no fallback, so a comparison shows exactly what that model wrote."""
    messages = [{"role": "user", "content": prompt}]
    if model in config.GROQ_JSON_MODE_MODELS:
        # JSON mode only checks that the reply is JSON, so the schema goes in the prompt;
        # the reply is still validated against it below
        schema_text = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        messages.insert(0, {"role": "system", "content": f"Reply with JSON only, matching this JSON schema:\n{schema_text}"})
        options = {"response_format": {"type": "json_object"}, "reasoning_effort": "none"}
    else:
        options = {"response_format": {"type": "json_schema", "json_schema": {
            "name": schema.__name__, "schema": strict_json_schema(schema), "strict": True}}}
    try:
        completion = _groq_client().chat.completions.create(
            model=model, messages=messages, temperature=0, **options)
        return schema.model_validate_json(completion.choices[0].message.content or ""), f"groq/{completion.model}"
    except groq.APIError as e:
        raise LLMError(f"Groq {model} failed ({type(e).__name__}: {e.message}).") from e
    except (ValidationError, IndexError) as e:
        raise LLMError(f"Groq {model} returned an answer in the wrong format.") from e


def chat_with_tools(contents: list[types.Content],
                    tools: list[types.FunctionDeclaration]) -> types.GenerateContentResponse:
    """One model turn that may request tool calls. Our code runs the tools, never the SDK."""
    response, _ = _generate_with_fallback(contents, types.GenerateContentConfig(
        temperature=0,
        tools=[types.Tool(function_declarations=tools)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    ))
    return response
