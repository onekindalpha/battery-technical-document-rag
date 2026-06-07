from __future__ import annotations

import json
import math
import re
import hashlib
import os
from collections import Counter
from pathlib import Path
from typing import Any

from app.document_processor import DocumentChunk
from app.schemas import SourceChunk

TOKEN_PATTERN = re.compile(r"[0-9A-Za-z가-힣_+-]+")
EMBEDDING_DIMENSIONS = 384


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


def dense_embedding(text: str) -> list[float]:
    sparse = embed_text(text)
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for token, weight in sparse.items():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign * weight
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_distance(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 1.0
    if len(left) > len(right):
        left, right = right, left
    similarity = sum(weight * right.get(token, 0.0) for token, weight in left.items())
    return 1.0 - similarity


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def lexical_overlap_score(query_tokens: set[str], text: str) -> float:
    if not query_tokens:
        return 0.0
    text_tokens = set(tokenize(text))
    return len(query_tokens & text_tokens) / len(query_tokens)


class VectorStore:
    def __init__(
        self,
        persist_path: Path,
        collection_name: str,
        embedding_model: str,
        vector_backend: str = "chroma",
    ):
        persist_path.mkdir(parents=True, exist_ok=True)
        self.store_path = persist_path / f"{collection_name}.json"
        self.embedding_model = embedding_model
        self.backend = "local"
        self.collection = None
        self.records = self._load()
        if vector_backend == "chroma":
            self._setup_chroma(persist_path, collection_name)

    def _setup_chroma(self, persist_path: Path, collection_name: str) -> None:
        try:
            os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
            import chromadb

            self.client = chromadb.PersistentClient(path=str(persist_path / "chroma"))
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self.backend = "chroma"
        except Exception:
            self.collection = None
            self.backend = "local"

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
        if self.collection is not None:
            self.collection.upsert(
                ids=[chunk.chunk_id for chunk in chunks],
                documents=[chunk.text for chunk in chunks],
                embeddings=[dense_embedding(chunk.text) for chunk in chunks],
                metadatas=[
                    {
                        "source": chunk.source,
                        "chunk_index": chunk.chunk_index,
                    }
                    for chunk in chunks
                ],
            )
            return len(chunks)

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
        records = self._all_records()
        dense_scores = self._dense_scores(query, records, max(top_k * 4, 12))
        bm25_scores = self._bm25_scores(query, records)
        candidate_ids = set(dense_scores)
        candidate_ids.update(
            record_id
            for record_id, _score in sorted(
                bm25_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )[: max(top_k * 4, 12)]
        )
        if not candidate_ids:
            return []

        max_bm25 = max((bm25_scores.get(record_id, 0.0) for record_id in candidate_ids), default=0.0)
        query_tokens = set(tokenize(query))
        scored_records: list[tuple[float, dict[str, Any]]] = []
        records_by_id = {str(record["id"]): record for record in records}

        for record_id in candidate_ids:
            record = records_by_id.get(record_id)
            if not record:
                continue
            dense_score = dense_scores.get(record_id, 0.0)
            bm25_score = bm25_scores.get(record_id, 0.0)
            normalized_bm25 = bm25_score / max_bm25 if max_bm25 else 0.0
            rerank_score = lexical_overlap_score(query_tokens, str(record["text"]))
            hybrid_score = (0.55 * dense_score) + (0.35 * normalized_bm25) + (0.10 * rerank_score)
            scored_records.append((hybrid_score, record))

        scored_records.sort(key=lambda item: item[0], reverse=True)
        return [
            SourceChunk(
                source=str(record["source"]),
                chunk_index=int(record["chunk_index"]),
                text=str(record["text"]),
                distance=round(1.0 - float(score), 4),
            )
            for score, record in scored_records[:top_k]
        ]

    def count(self) -> int:
        if self.collection is not None:
            return int(self.collection.count())
        return len(self.records)

    def sources(self) -> list[str]:
        if self.collection is not None:
            return sorted({str(record["source"]) for record in self._all_records()})
        return sorted({str(record["source"]) for record in self.records.values()})

    def _all_records(self) -> list[dict[str, Any]]:
        if self.collection is None:
            return [
                {
                    "id": record_id,
                    "source": record["source"],
                    "chunk_index": record["chunk_index"],
                    "text": record["text"],
                    "embedding": record.get("embedding"),
                }
                for record_id, record in self.records.items()
            ]

        result = self.collection.get(include=["documents", "metadatas"])
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        records = []
        for record_id, document, metadata in zip(ids, documents, metadatas, strict=False):
            metadata = metadata or {}
            records.append(
                {
                    "id": record_id,
                    "source": metadata.get("source", "unknown"),
                    "chunk_index": metadata.get("chunk_index", 0),
                    "text": document or "",
                }
            )
        return records

    def _dense_scores(
        self,
        query: str,
        records: list[dict[str, Any]],
        candidate_k: int,
    ) -> dict[str, float]:
        if self.collection is not None:
            result = self.collection.query(
                query_embeddings=[dense_embedding(query)],
                n_results=min(candidate_k, max(self.count(), 1)),
                include=["distances"],
            )
            ids = result.get("ids", [[]])[0]
            distances = result.get("distances", [[]])[0]
            return {
                str(record_id): 1.0 / (1.0 + float(distance))
                for record_id, distance in zip(ids, distances, strict=False)
            }

        query_embedding = embed_text(query)
        scored: list[tuple[str, float]] = []
        for record in records:
            embedding = record.get("embedding")
            if not isinstance(embedding, dict):
                continue
            similarity = 1.0 - cosine_distance(query_embedding, embedding)
            scored.append((str(record["id"]), similarity))
        scored.sort(key=lambda item: item[1], reverse=True)
        return dict(scored[:candidate_k])

    def _bm25_scores(self, query: str, records: list[dict[str, Any]]) -> dict[str, float]:
        query_tokens = tokenize(query)
        if not query_tokens or not records:
            return {}

        tokenized_documents = [tokenize(str(record["text"])) for record in records]
        document_count = len(tokenized_documents)
        average_length = sum(len(document) for document in tokenized_documents) / max(document_count, 1)
        document_frequency: Counter[str] = Counter()
        for document in tokenized_documents:
            document_frequency.update(set(document))

        k1 = 1.5
        b = 0.75
        scores: dict[str, float] = {}
        for record, document in zip(records, tokenized_documents, strict=False):
            frequencies = Counter(document)
            document_length = len(document)
            score = 0.0
            for token in query_tokens:
                frequency = frequencies.get(token, 0)
                if frequency == 0:
                    continue
                idf = math.log(
                    1
                    + (document_count - document_frequency[token] + 0.5)
                    / (document_frequency[token] + 0.5)
                )
                denominator = frequency + k1 * (1 - b + b * document_length / max(average_length, 1))
                score += idf * (frequency * (k1 + 1)) / denominator
            scores[str(record["id"])] = score
        return scores
