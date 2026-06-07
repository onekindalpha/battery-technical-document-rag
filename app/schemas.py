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


class RetrievalEvalCase(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    expected_sources: list[str] = Field(min_length=1)


class RetrievalEvalRequest(BaseModel):
    cases: list[RetrievalEvalCase] = Field(min_length=1, max_length=50)
    top_k: int = Field(default=3, ge=1, le=10)


class RetrievalEvalCaseResult(BaseModel):
    question: str
    expected_sources: list[str]
    retrieved_sources: list[str]
    hit: bool
    reciprocal_rank: float
    precision_at_k: float


class RetrievalEvalResponse(BaseModel):
    top_k: int
    total_cases: int
    hit_at_k: float
    mrr: float
    mean_precision_at_k: float
    results: list[RetrievalEvalCaseResult]
