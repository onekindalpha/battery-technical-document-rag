from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from app.document_processor import DocumentChunk
from app.schemas import SourceChunk

TOKEN_PATTERN = re.compile(r"[0-9A-Za-z가-힣_+-]+")


def embed_text(text: str) -> dict[str, float]:
    tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
    features: Counter[str] = Counter(tokens)
    compact_text = "".join(tokens)
    for size in (2, 3):
        for index in range(max(0, len(compact_text) - size + 1)):
            features[f"char:{compact_text[index:index + size]}"] += 0.35
    norm = math.sqrt(sum(value * value for value in features.values()))
    if norm == 0:
        return {}
    return {key: value / norm for key, value in features.items()}


def cosine_distance(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 1.0
    if len(left) > len(right):
        left, right = right, left
    similarity = sum(weight * right.get(token, 0.0) for token, weight in left.items())
    return 1.0 - similarity


class VectorStore:
    def __init__(self, persist_path: Path, collection_name: str, embedding_model: str):
        persist_path.mkdir(parents=True, exist_ok=True)
        self.store_path = persist_path / f"{collection_name}.json"
        self.embedding_model = embedding_model
        self.records = self._load()

    def _load(self) -> dict[str, dict[str, object]]:
        if not self.store_path.exists():
            return {}
        with self.store_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _persist(self) -> None:
        temporary_path = self.store_path.with_suffix(".tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(self.records, file, ensure_ascii=False)
        temporary_path.replace(self.store_path)

    def add(self, chunks: list[DocumentChunk]) -> int:
        if not chunks:
            return 0
        for chunk in chunks:
            self.records[chunk.chunk_id] = {
                "source": chunk.source,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "embedding": embed_text(chunk.text),
            }
        self._persist()
        return len(chunks)

    def search(self, query: str, top_k: int) -> list[SourceChunk]:
        if self.count() == 0:
            return []
        query_embedding = embed_text(query)
        scored_records: list[tuple[float, dict[str, object]]] = []
        for record in self.records.values():
            embedding = record["embedding"]
            if not isinstance(embedding, dict):
                continue
            distance = cosine_distance(query_embedding, embedding)
            scored_records.append((distance, record))
        scored_records.sort(key=lambda item: item[0])
        return [
            SourceChunk(
                source=str(record["source"]),
                chunk_index=int(record["chunk_index"]),
                text=str(record["text"]),
                distance=float(distance),
            )
            for distance, record in scored_records[:top_k]
        ]

    def count(self) -> int:
        return len(self.records)

    def sources(self) -> list[str]:
        return sorted({str(record["source"]) for record in self.records.values()})
