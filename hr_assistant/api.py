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
from hr_assistant.employees import get_employee, list_employees
from hr_assistant.llm import LLMError
from hr_assistant.retrieval import get_collection

logger = logging.getLogger(__name__)

app = FastAPI(
    title="HR Assistant API",
    description="Answers employee questions using the company HR regulation, with source sections.",
    version="1.0.0",
)

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class AskRequest(BaseModel):
    question: Question = Field(examples=["Kaç gün yıllık iznim kaldı?"])
    # Demo only: in production the employee comes from the authenticated session, not the request body
    employee_id: str | None = Field(default=None, examples=["E1002"])


class AskResponse(BaseModel):
    answer: str
    sections: list[str] = Field(description="Regulation sections the answer is based on.")
    refused: bool = Field(description="True when the answer is not based on the regulation.")
    missing_info: list[str] = Field(description="Parts of the question the regulation does not cover.")
    tools_used: list[str] = Field(description="Tools the model called while gathering information.")


class EmployeeSummary(BaseModel):
    id: str
    name: str
    department: str


class HealthResponse(BaseModel):
    status: str
    indexed_chunks: int


@app.get("/health")
def health() -> HealthResponse:
    count = get_collection().count()
    if count == 0:
        # Without indexed sections every question would be refused
        raise HTTPException(status_code=503, detail="No sections indexed. Run: python -m hr_assistant.ingest")
    return HealthResponse(status="ok", indexed_chunks=count)


@app.get("/employees")
def employees() -> list[EmployeeSummary]:
    """Demo employees to sign in as."""
    return [EmployeeSummary(id=e.id, name=e.name, department=e.department) for e in list_employees()]


@app.post("/ask")
def ask(request: AskRequest) -> AskResponse:
    employee = None
    if request.employee_id:
        employee = get_employee(request.employee_id)
        if employee is None:
            raise HTTPException(status_code=404, detail="Employee not found.")
    # A plain "def" endpoint runs in a worker thread, so slow model calls do not block other requests
    try:
        result = answer_question(request.question, employee)
    except LLMError:
        logger.exception("Language model request failed")
        raise HTTPException(status_code=503, detail="Language model is unavailable, try again later.")
    return AskResponse(**asdict(result))