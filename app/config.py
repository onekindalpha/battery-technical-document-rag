from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    vector_backend: str = os.getenv("VECTOR_BACKEND", "local")
    vector_store_path: Path = Path(os.getenv("VECTOR_STORE_PATH", "data/vector_store"))
    collection_name: str = os.getenv("COLLECTION_NAME", "battery_technical_documents")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "hashing-char-ngram-v1")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    api_auth_token: str = os.getenv("API_AUTH_TOKEN", "")
    request_log_db_path: Path = Path(os.getenv("REQUEST_LOG_DB_PATH", "data/request_logs.sqlite3"))
    redis_url: str = os.getenv("REDIS_URL", "")
    top_k: int = int(os.getenv("TOP_K", "3"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "900"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    upload_path: Path = Path("data/uploads")
    knowledge_base_path: Path = Path("data/knowledge_base")


settings = Settings()
