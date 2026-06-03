# Battery Technical Document RAG Assistant

Battery RUL AI Inference System에서 확장한 기술문서 RAG Assistant입니다. 배터리 RUL 프로젝트의 README, 실험 메모, 논문 요약, 데이터 검증 기준, BMS 운영 관점 문서를 검색하고, 관련 근거 chunk를 기반으로 답변을 생성합니다.

이 프로젝트는 단순 챗봇이 아니라, Battery RUL 포트폴리오를 설명하고 다음 실험·PoC 방향을 검토하기 위한 **RAG 기반 Research Copilot MVP**로 설계했습니다. 현재는 문서 업로드, chunking, 검색, citation 기반 답변을 구현했으며, 향후 실험 계획 생성, 데이터 누수 체크리스트 생성, PoC 후보 제안 같은 agentic workflow로 확장할 수 있습니다.

## Why this project

기존 [Battery RUL AI Inference System](https://github.com/onekindalpha/battery-rul-ai-inference-system)은 시계열 기반 RUL 예측 결과를 API·대시보드·배포 환경으로 연결합니다. 이 프로젝트는 그 위에 기술문서 검색 계층을 추가해, 모델 설계 의도와 데이터 검증 기준을 문서 근거와 함께 설명할 수 있도록 만든 별도 AI service PoC입니다.

Battery RUL 모델은 모델 성능 수치만으로 운영 활용성을 설명하기 어렵습니다. 초기 cycle 기반 예측에서는 데이터 누수 여부, 배터리별 실험 조건 차이, 관측 비율, feature 품질, 불확실성 표시 방식까지 함께 검토해야 합니다. 이 RAG Assistant는 이러한 판단 기준을 문서화하고, 질문이 들어오면 관련 근거를 찾아 답변하는 흐름을 구현합니다.

## Features

- PDF, Markdown, TXT 기술문서 업로드
- 문서 정규화, chunk 분할, metadata 생성
- Lightweight lexical embedding
- JSON-backed persistent vector store with cosine similarity search
- cosine similarity 기반 근거 검색
- Groq LLM 기반 RAG 답변 생성
- 답변별 문서명·chunk 번호 표시
- API 키가 없는 환경을 위한 retrieval-only fallback
- FastAPI API와 lightweight web UI
- Docker 기반 실행
- 예시 질문 기반 portfolio demo flow

## Architecture

```mermaid
flowchart LR
    A["Battery PDF / Markdown / TXT"] --> B["Document processor"]
    B --> C["Chunking + metadata"]
    C --> D["Lexical embedding"]
    D --> E["Persistent Vector Store"]
    Q["User question"] --> F["Similarity search"]
    E --> F
    F --> G["Retrieved source chunks"]
    G --> H["Groq LLM prompt"]
    H --> I["Answer with citations"]
    G --> J["Retrieval-only fallback"]
```

## Run locally

Python 3.11 or 3.12 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

Open `http://localhost:7860`.

## API

```bash
curl http://localhost:7860/api/health

curl -X POST http://localhost:7860/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"초기 cycle 기반 RUL 예측에서 확인할 항목은 무엇인가요?"}'
```

Interactive API documentation is available at `http://localhost:7860/docs`.

## Environment variables

| Variable | Description |
| --- | --- |
| `GROQ_API_KEY` | Optional. Enables generated RAG answers. |
| `GROQ_MODEL` | Groq chat model identifier. |
| `VECTOR_STORE_PATH` | Local vector store persistence path. |
| `EMBEDDING_MODEL` | Embedding mode label. |
| `TOP_K` | Number of retrieved source chunks. |
| `CHUNK_SIZE` | Character length of each chunk. |
| `CHUNK_OVERLAP` | Overlap between adjacent chunks. |

`data/sample_docs`에는 공개 데모를 위한 짧은 배터리 RUL 설명 문서가 포함되어 있습니다. 논문 원문을 복제하지 않고, 프로젝트에서 확인한 문제의식과 운영 관점을 직접 정리한 샘플 코퍼스입니다.

## Portfolio scope

This repository is intentionally separate from the Battery RUL inference repository. It demonstrates a second AI service pattern:

1. Inference application: time-series model serving and visualization
2. Document RAG application: ingestion, retrieval, grounded generation, and citations
3. Research Copilot direction: experiment planning, data quality checklist generation, and PoC proposal support

## Security note

Do not commit API keys. Store secrets only in `.env` locally or in the deployment platform's secret manager.
