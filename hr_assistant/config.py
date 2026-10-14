"""Central settings for the HR assistant."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENT_PATH = PROJECT_ROOT / "documents" / "hr_regulation.pdf"
DB_PATH = PROJECT_ROOT / "chroma_db"
EVAL_CASES_PATH = PROJECT_ROOT / "eval" / "test_cases.json"
COLLECTION_NAME = "hr_regulation"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GENERATION_MODELS = ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3.8-flash"]
EMBEDDING_MODEL = "gemini-embedding-001"

TOP_K = 5
SIMILARITY_THRESHOLD = 0.6

# Free tier allows about 100 embedding requests per minute
EMBED_BATCH_SIZE = 20
EMBED_BATCH_PAUSE_SECONDS = 15