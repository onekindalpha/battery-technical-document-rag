from __future__ import annotations

from groq import Groq

from app.schemas import SourceChunk

SYSTEM_PROMPT = """You are a battery technical document assistant.
Answer only from the supplied context. If the context is insufficient, say so clearly.
Write the answer in Korean. Cite evidence with labels such as [source.md#0].
Do not invent values, experimental conditions, or conclusions."""


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
            f"[{source.citation}]\n{source.text}" for source in sources
        )
        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"질문: {question}\n\n검색 문맥:\n{context}",
                },
            ],
        )
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

