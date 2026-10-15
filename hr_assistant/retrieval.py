"""Vector store access and semantic search."""
from dataclasses import dataclass
from functools import cache

import chromadb
from chromadb.api.models.Collection import Collection

from hr_assistant import config, llm


@dataclass(frozen=True)
class SearchHit:
    section: str
    page: int
    path: str  # where the section sits in the document, e.g. "5. ... > 5.7. ..."
    text: str
    score: float


@dataclass(frozen=True)
class RegulationSection:
    section: str
    page: int
    path: str
    text: str


@cache
def get_collection() -> Collection:
    db = chromadb.PersistentClient(path=str(config.DB_PATH))
    return db.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def split_chunk(stored_text: str) -> tuple[str, str]:
    # Chunks are stored as "path\nsection text"; top-level sections have no path
    path, _, body = stored_text.rpartition("\n")
    return path, body


def search(question: str, top_k: int = config.TOP_K,
           threshold: float = config.SIMILARITY_THRESHOLD) -> list[SearchHit]:
    result = get_collection().query(query_embeddings=llm.embed([question]), n_results=top_k)
    hits = []
    for text, meta, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        similarity = 1 - distance  # Chroma returns cosine distance
        if similarity >= threshold:
            path, body = split_chunk(text)
            hits.append(SearchHit(section=meta["section"], page=meta["page"],
                                  path=path, text=body, score=similarity))
    return hits


def get_sections(numbers: list[str]) -> list[RegulationSection]:
    """Full text of the given sections, in the given order. Unknown numbers are skipped.

    Section numbers are treated as unique, as everywhere else in the pipeline.
    """
    if not numbers:
        return []
    result = get_collection().get(where={"section": {"$in": numbers}}, include=["documents", "metadatas"])
    found: dict[str, RegulationSection] = {}
    for text, meta in zip(result["documents"], result["metadatas"]):
        path, body = split_chunk(text)
        found.setdefault(meta["section"], RegulationSection(
            section=meta["section"], page=meta["page"], path=path, text=body))
    return [found[n] for n in numbers if n in found]
