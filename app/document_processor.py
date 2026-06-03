from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    source: str
    chunk_index: int
    text: str


def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    return path.read_text(encoding="utf-8")


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be between 0 and chunk_size - 1")

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - chunk_overlap
    return chunks


def create_chunks(path: Path, chunk_size: int, chunk_overlap: int) -> list[DocumentChunk]:
    text_chunks = split_text(read_document(path), chunk_size, chunk_overlap)
    chunks: list[DocumentChunk] = []
    for index, text in enumerate(text_chunks):
        digest = hashlib.sha256(f"{path.name}:{index}:{text}".encode()).hexdigest()[:20]
        chunks.append(
            DocumentChunk(
                chunk_id=digest,
                source=path.name,
                chunk_index=index,
                text=text,
            )
        )
    return chunks

