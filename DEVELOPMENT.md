# Development Notes

This file contains local setup, API examples, retrieval evaluation commands, environment variables, Docker Compose usage, and security notes for Battery Technical Document RAG Assistant.

## Run Locally

Python 3.11 or 3.12 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

Open:

```text
http://localhost:7860
```

## Docker Compose

```bash
docker compose up --build
```

This starts the FastAPI app and a Redis container for answer caching.

## API

```bash
curl http://localhost:7860/api/health
```

```bash
curl -X POST http://localhost:7860/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"초기 cycle 기반 RUL 예측에서 확인할 항목은 무엇인가요?"}'
```

Interactive API documentation is available at:

```text
http://localhost:7860/docs
```

## Retrieval Evaluation

```bash
curl -X POST http://localhost:7860/api/eval/retrieval \
  -H 'Content-Type: application/json' \
  -d '{
    "top_k": 3,
    "cases": [
      {
        "question": "RUL과 SoH는 무엇이 다른가요?",
        "expected_sources": ["battery_rul_basics.md"]
      }
    ]
  }'
```

When `API_AUTH_TOKEN` is set, protected endpoints require:

```bash
-H 'X-API-Key: your-api-token'
```

## Environment Variables

| Variable | Description |
| --- | --- |
| `GROQ_API_KEY` | Optional. Enables generated RAG answers. |
| `GROQ_MODEL` | Groq chat model identifier. |
| `API_AUTH_TOKEN` | Optional. Enables API key protection for ask, ingest, and evaluation endpoints. |
| `VECTOR_BACKEND` | `local` or `chroma`. Defaults to `local` for demo stability. |
| `VECTOR_STORE_PATH` | Local vector store persistence path. |
| `EMBEDDING_MODEL` | Embedding mode label. |
| `REQUEST_LOG_DB_PATH` | SQLite path for API request logs. |
| `REDIS_URL` | Optional Redis URL for answer cache. |
| `TOP_K` | Number of retrieved source chunks. |
| `CHUNK_SIZE` | Character length of each chunk. |
| `CHUNK_OVERLAP` | Overlap between adjacent chunks. |

## Security Note

Do not commit API keys. Store secrets only in `.env` locally or in the deployment platform's secret manager.
