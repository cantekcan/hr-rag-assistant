"""HTTP API for the HR assistant.

Run with: uvicorn hr_assistant.api:app --reload
Interactive docs: http://127.0.0.1:8000/docs
"""
import logging
from dataclasses import asdict
from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, StringConstraints

from hr_assistant.answer import answer_question
from hr_assistant.retrieval import get_collection

logger = logging.getLogger(__name__)

app = FastAPI(
    title="HR Assistant API",
    description="Answers employee questions using the company HR regulation, with source sections.",
    version="1.0.0",
)

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class AskRequest(BaseModel):
    question: Question = Field(examples=["Evlenirsem kaç gün izin alırım?"])


class AskResponse(BaseModel):
    answer: str
    sections: list[str] = Field(description="Regulation sections the answer is based on.")
    refused: bool = Field(description="True when the answer is not based on the regulation.")
    missing_info: list[str] = Field(description="Parts of the question the regulation does not cover.")


class HealthResponse(BaseModel):
    status: str
    indexed_chunks: int


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok", indexed_chunks=get_collection().count())


@app.post("/ask")
def ask(request: AskRequest) -> AskResponse:
    # A plain "def" endpoint runs in a worker thread, so slow model calls do not block other requests
    try:
        result = answer_question(request.question)
    except RuntimeError:
        logger.exception("Language model request failed")
        raise HTTPException(status_code=503, detail="Language model is unavailable, try again later.")
    return AskResponse(**asdict(result))