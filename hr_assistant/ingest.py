"""Reads the regulation PDF, splits it into sections and stores them in the vector database.

Run with: python -m hr_assistant.ingest
Safe to run repeatedly: only sections that are not stored yet are embedded.
"""
import re
import time
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from hr_assistant import config, llm
from hr_assistant.retrieval import get_collection

SECTION_START = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(.*)")
PAGE_NUMBER_LINE = re.compile(r"Sayfa \d+")
MIN_SECTION_LENGTH = 30  # shorter sections are headings only; their content lives in sub-sections


@dataclass
class Section:
    number: str
    text: str
    page: int


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    section: str
    page: int


def read_sections(pdf_path: Path) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    for page_no, page in enumerate(PdfReader(pdf_path).pages, start=1):
        for line in (page.extract_text() or "").split("\n"):
            line = line.strip()
            if not line or PAGE_NUMBER_LINE.fullmatch(line):
                continue
            if match := SECTION_START.match(line):
                current = Section(number=match.group(1), text=line, page=page_no)
                sections.append(current)
            elif current:
                current.text += " " + line
    return sections


def _short_title(text: str, max_length: int = 80) -> str:
    return re.split(r"[:;]", text, maxsplit=1)[0][:max_length].strip()


def build_chunks(sections: list[Section]) -> list[Chunk]:
    titles = {s.number: _short_title(s.text) for s in sections}
    chunks = []
    for index, s in enumerate(sections):
        if len(s.text) < MIN_SECTION_LENGTH:
            continue
        parts = s.number.split(".")
        parent_numbers = [".".join(parts[:i]) for i in range(1, len(parts))]
        path = " > ".join(titles[n] for n in parent_numbers if n in titles)
        chunks.append(Chunk(
            id=f"{index:04d}-{s.number}",
            text=f"{path}\n{s.text}" if path else s.text,
            section=s.number,
            page=s.page,
        ))
    return chunks


def index_chunks(chunks: list[Chunk]) -> None:
    collection = get_collection()
    existing_ids = set(collection.get(include=[])["ids"])
    pending = [c for c in chunks if c.id not in existing_ids]
    print(f"{len(existing_ids)} chunks already indexed, {len(pending)} remaining.")

    size = config.EMBED_BATCH_SIZE
    for i in range(0, len(pending), size):
        batch = pending[i:i + size]
        collection.add(
            ids=[c.id for c in batch],
            documents=[c.text for c in batch],
            embeddings=llm.embed([c.text for c in batch]),
            metadatas=[{"section": c.section, "page": c.page} for c in batch],
        )
        print(f"{min(i + size, len(pending))}/{len(pending)} chunks indexed")
        if i + size < len(pending):
            time.sleep(config.EMBED_BATCH_PAUSE_SECONDS)

    print(f"Done. Collection has {collection.count()} chunks.")


def main() -> None:
    sections = read_sections(config.DOCUMENT_PATH)
    chunks = build_chunks(sections)
    print(f"{len(sections)} sections found, {len(chunks)} chunks created.")
    index_chunks(chunks)


if __name__ == "__main__":
    main()