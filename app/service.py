from __future__ import annotations

import shutil
from pathlib import Path

from app.config import settings
from app.document_processor import SUPPORTED_EXTENSIONS, create_chunks
from app.llm_service import LLMService
from app.schemas import AskResponse, IngestResponse
from app.vector_store import VectorStore


class DocumentRAGService:
    def __init__(self):
        self.vector_store = VectorStore(
            settings.vector_store_path,
            settings.collection_name,
            settings.embedding_model,
        )
        self.llm = LLMService(settings.groq_api_key, settings.groq_model)
        settings.upload_path.mkdir(parents=True, exist_ok=True)

    def ingest_paths(self, paths: list[Path], copy_uploads: bool = True) -> IngestResponse:
        files: list[str] = []
        chunks_added = 0
        for source_path in paths:
            if source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise ValueError(f"Unsupported file type: {source_path.suffix}")
            target_path = settings.upload_path / source_path.name
            if copy_uploads and source_path.resolve() != target_path.resolve():
                shutil.copy2(source_path, target_path)
            else:
                target_path = source_path
            chunks_added += self.vector_store.add(
                create_chunks(target_path, settings.chunk_size, settings.chunk_overlap)
            )
            files.append(target_path.name)
        return IngestResponse(files=files, chunks_added=chunks_added)

    def ingest_samples_if_empty(self) -> None:
        if self.vector_store.count() != 0:
            return
        paths = sorted(settings.sample_docs_path.glob("*"))
        self.ingest_paths(paths, copy_uploads=False)

    def ask(self, question: str, top_k: int | None = None) -> AskResponse:
        sources = self.vector_store.search(question, top_k or settings.top_k)
        answer, mode = self.llm.answer(question, sources)
        return AskResponse(answer=answer, sources=sources, mode=mode)

    def sources(self) -> list[str]:
        return self.vector_store.sources()


service = DocumentRAGService()
