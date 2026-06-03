from __future__ import annotations

from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    source: str
    chunk_index: int
    text: str
    distance: float | None = None

    @property
    def citation(self) -> str:
        return f"{self.source}#{self.chunk_index}"


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=10)


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    mode: str
    response_time_ms: float


class IngestResponse(BaseModel):
    files: list[str]
    chunks_added: int
