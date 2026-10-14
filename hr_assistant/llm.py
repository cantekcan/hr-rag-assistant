"""Gemini access: embeddings and structured generation, with retry and model fallback."""
import time
from collections.abc import Callable
from functools import cache
from typing import TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from hr_assistant import config

T = TypeVar("T")
SchemaT = TypeVar("SchemaT", bound=BaseModel)


@cache
def _client() -> genai.Client:
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to the .env file.")
    return genai.Client(api_key=config.GEMINI_API_KEY)


def _with_retry(operation: Callable[[], T], max_attempts: int = 5) -> T:
    for attempt in range(max_attempts):
        try:
            return operation()
        except errors.APIError as e:
            if e.code == 429:
                print("Quota exceeded, waiting 60 seconds...")
                time.sleep(60)
            elif e.code >= 500:
                wait = 2 ** attempt
                print(f"Server busy, waiting {wait} seconds...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Embedding request failed, try again in a few minutes.")


def embed(texts: list[str]) -> list[list[float]]:
    result = _with_retry(lambda: _client().models.embed_content(
        model=config.EMBEDDING_MODEL, contents=texts))
    return [e.values for e in result.embeddings]


def generate(prompt: str, schema: type[SchemaT], rounds: int = 3) -> SchemaT:
    """Ask the model for JSON matching `schema` and return it as a typed object."""
    generation_config = types.GenerateContentConfig(
        temperature=0,  # consistent answers for the same question
        response_mime_type="application/json",
        response_schema=schema,
    )
    for r in range(rounds):
        for model in config.GENERATION_MODELS:
            try:
                response = _client().models.generate_content(
                    model=model, contents=prompt, config=generation_config)
                return response.parsed or schema.model_validate_json(response.text)
            except errors.APIError as e:
                print(f"{model} unavailable ({e.code})")
        wait = 5 * (r + 1)
        print(f"All models busy, retrying in {wait} seconds...")
        time.sleep(wait)
    raise RuntimeError("No model responded, try again in a few minutes.")