from __future__ import annotations

from collections.abc import Callable

from app.schemas import (
    RetrievalEvalCase,
    RetrievalEvalCaseResult,
    RetrievalEvalResponse,
    SourceChunk,
)

SearchFunction = Callable[[str, int], list[SourceChunk]]


def evaluate_retrieval_cases(
    cases: list[RetrievalEvalCase],
    top_k: int,
    search: SearchFunction,
) -> RetrievalEvalResponse:
    results: list[RetrievalEvalCaseResult] = []

    for case in cases:
        retrieved = search(case.question, top_k)
        retrieved_sources = [source.source for source in retrieved]
        expected = set(case.expected_sources)
        first_rank = 0
        relevant_count = 0

        for index, source_name in enumerate(retrieved_sources, start=1):
            if source_name in expected:
                relevant_count += 1
                if first_rank == 0:
                    first_rank = index

        reciprocal_rank = round(1 / first_rank, 4) if first_rank else 0.0
        precision_at_k = round(relevant_count / max(top_k, 1), 4)
        results.append(
            RetrievalEvalCaseResult(
                question=case.question,
                expected_sources=case.expected_sources,
                retrieved_sources=retrieved_sources,
                hit=first_rank > 0,
                reciprocal_rank=reciprocal_rank,
                precision_at_k=precision_at_k,
            )
        )

    total = len(results)
    denominator = max(total, 1)
    return RetrievalEvalResponse(
        top_k=top_k,
        total_cases=total,
        hit_at_k=round(sum(1 for result in results if result.hit) / denominator, 4),
        mrr=round(sum(result.reciprocal_rank for result in results) / denominator, 4),
        mean_precision_at_k=round(
            sum(result.precision_at_k for result in results) / denominator,
            4,
        ),
        results=results,
    )
