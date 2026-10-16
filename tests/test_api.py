"""API behaviour with the answer pipeline replaced by a fake, so no model or vector store is needed."""
import pytest
from fastapi.testclient import TestClient

from hr_assistant import api, config
from hr_assistant.answer import AnswerResult
from hr_assistant.llm import LLMError
from hr_assistant.rate_limit import RateLimiter
from hr_assistant.retrieval import RegulationSection

SOURCE = RegulationSection(section="5.7.4.2", page=7, path="5.7. İzinler > 5.7.4. Yıllık izin",
                           text="5.7.4.2. Beş-onbeş yıl arası (onbeş yıl dahil) yirmi iş günü,")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "limiter", RateLimiter(per_client=0, total=0))  # tests are not rate limited
    return TestClient(api.app)


def answer_with(result=None, error=None):
    def fake(question, employee=None, today=None):
        if error:
            raise error
        return result
    return fake


def test_chat_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "İK Asistanı" in response.text


def test_answer_includes_source_text(client, monkeypatch):
    result = AnswerResult(answer="Kalan izniniz 8 gündür.", sections=["5.7.4.2"], sources=[SOURCE])
    monkeypatch.setattr(api, "answer_question", answer_with(result))
    body = client.post("/ask", json={"question": "Kaç gün iznim kaldı?"}).json()
    assert body["sections"] == ["5.7.4.2"]
    assert body["sources"][0]["text"] == SOURCE.text


def test_answer_includes_missing_info_note(client, monkeypatch):
    note = "Yönetmelikte şu konularda bilgi bulunmuyor: tazminat."
    result = AnswerResult(answer=f"Kalan izniniz 8 gündür.\n\n{note}", missing_info=["tazminat"],
                          missing_info_note=note)
    monkeypatch.setattr(api, "answer_question", answer_with(result))
    body = client.post("/ask", json={"question": "İznim ve tazminatım?"}).json()
    assert body["missing_info_note"] == note
    assert body["answer"].endswith(note)


def test_model_failure_returns_503(client, monkeypatch):
    monkeypatch.setattr(api, "answer_question", answer_with(error=LLMError("down")))
    assert client.post("/ask", json={"question": "Deneme süresi?"}).status_code == 503


def test_unknown_employee_returns_404(client):
    assert client.post("/ask", json={"question": "İznim?", "employee_id": "NOPE"}).status_code == 404


@pytest.mark.parametrize("question", ["", "   ", "a" * 1001])
def test_invalid_question_returns_422(client, question):
    assert client.post("/ask", json={"question": question}).status_code == 422


def test_document_is_served_inline(client, monkeypatch, tmp_path):
    pdf = tmp_path / "hr_regulation.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    monkeypatch.setattr(config, "DOCUMENT_PATH", pdf)
    response = client.get("/document")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")


def test_missing_document_returns_404(client, monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DOCUMENT_PATH", tmp_path / "missing.pdf")
    assert client.get("/document").status_code == 404


def test_too_many_questions_returns_429(client, monkeypatch):
    monkeypatch.setattr(api, "limiter", RateLimiter(per_client=1, total=100))
    monkeypatch.setattr(api, "answer_question", answer_with(AnswerResult(answer="Tamam.")))
    assert client.post("/ask", json={"question": "Bir"}).status_code == 200
    response = client.post("/ask", json={"question": "İki"})
    assert response.status_code == 429
    assert "retry-after" in response.headers
