from __future__ import annotations

from groq import APIStatusError, Groq, RateLimitError

from app.schemas import SourceChunk

SYSTEM_PROMPT = """You are a battery technical document assistant.
Answer only from the supplied context. If the context is insufficient, say so clearly.
Write the answer in Korean. Cite evidence with labels such as [source.md#0].
Do not invent values, experimental conditions, or conclusions.
Avoid repeating the same point. Merge overlapping evidence into one concise answer."""

MAX_CONTEXT_CHARS_PER_SOURCE = 520


class LLMService:
    def __init__(self, api_key: str, model: str):
        self.model = model
        self.client = Groq(api_key=api_key) if api_key else None

    def answer(self, question: str, sources: list[SourceChunk]) -> tuple[str, str]:
        if not sources:
            return (
                "검색된 문서가 없습니다. 먼저 배터리 기술문서를 업로드해 주세요.",
                "retrieval-only",
            )
        if self.client is None:
            return self._retrieval_only_answer(sources), "retrieval-only"

        context = "\n\n".join(
            f"[{source.citation}]\n{source.text[:MAX_CONTEXT_CHARS_PER_SOURCE]}"
            for source in sources
        )
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                max_tokens=520,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"질문: {question}\n\n검색 문맥:\n{context}",
                    },
                ],
            )
        except RateLimitError:
            return self._rate_limit_fallback(sources), "rate-limit-fallback"
        except APIStatusError as error:
            return self._api_error_fallback(sources, error.status_code), "api-error-fallback"
        except Exception as error:
            return self._generic_error_fallback(sources, error), "llm-error-fallback"
        return completion.choices[0].message.content or "", "rag-generation"

    @staticmethod
    def _retrieval_only_answer(sources: list[SourceChunk]) -> str:
        excerpts = "\n\n".join(
            f"- [{source.citation}] {source.text[:260]}..." for source in sources
        )
        return (
            "현재 LLM API 키가 설정되지 않아 검색 결과만 제공합니다. "
            "아래 문서 구간을 기준으로 질문을 검토해 주세요.\n\n"
            f"{excerpts}"
        )

    @staticmethod
    def _rate_limit_fallback(sources: list[SourceChunk]) -> str:
        excerpts = "\n\n".join(
            f"- [{source.citation}] {source.text[:320]}..." for source in sources
        )
        return (
            "현재 LLM API 사용량 제한에 걸려 생성형 답변 대신 검색 근거를 제공합니다. "
            "잠시 후 다시 질문하면 LLM 기반 답변이 생성됩니다.\n\n"
            f"{excerpts}"
        )

    @staticmethod
    def _api_error_fallback(sources: list[SourceChunk], status_code: int) -> str:
        excerpts = "\n\n".join(
            f"- [{source.citation}] {source.text[:320]}..." for source in sources
        )
        return (
            f"LLM API 호출 중 오류가 발생했습니다. 상태 코드: {status_code}. "
            "아래 검색 근거를 기준으로 먼저 검토해 주세요.\n\n"
            f"{excerpts}"
        )

    @staticmethod
    def _generic_error_fallback(sources: list[SourceChunk], error: Exception) -> str:
        excerpts = "\n\n".join(
            f"- [{source.citation}] {source.text[:320]}..." for source in sources
        )
        return (
            "LLM 응답 생성 중 일시적인 오류가 발생해 검색 근거를 먼저 제공합니다. "
            f"오류 유형: {type(error).__name__}. "
            "질문이 현재 문서 범위를 벗어난 경우에는 관련 문서를 추가하거나, 질문을 Battery RUL 운영·데이터 품질·모델 추론 관점으로 좁혀 주세요.\n\n"
            f"{excerpts}"
        )
