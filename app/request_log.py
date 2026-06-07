from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class RequestLog:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    question TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    response_time_ms REAL NOT NULL,
                    source_count INTEGER NOT NULL
                )
                """
            )

    def record(self, question: str, mode: str, response_time_ms: float, source_count: int) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO rag_requests (
                    created_at, question, mode, response_time_ms, source_count
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(timespec="seconds"),
                    question,
                    mode,
                    response_time_ms,
                    source_count,
                ),
            )
