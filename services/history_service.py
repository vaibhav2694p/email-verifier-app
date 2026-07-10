from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class HistoryService:
    def __init__(self, database_url: str = "sqlite:///email_verifier.db") -> None:
        self.path = _sqlite_path(database_url)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS verification_runs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS verification_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def save_run(self, run_id: str, metadata: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO verification_runs (id, created_at, metadata) VALUES (?, ?, ?)",
                (run_id, datetime.now(timezone.utc).isoformat(), json.dumps(metadata, default=str)),
            )

    def save_result(self, run_id: str, email: str, result: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO verification_results (run_id, email, result_json, created_at) VALUES (?, ?, ?, ?)",
                (run_id, email, json.dumps(result, default=str), datetime.now(timezone.utc).isoformat()),
            )

    def list_runs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, created_at, metadata FROM verification_runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r[0], "created_at": r[1], "metadata": json.loads(r[2])} for r in rows]


def _sqlite_path(database_url: str) -> Path:
    if database_url.startswith("sqlite:///"):
        return Path(database_url.replace("sqlite:///", "", 1))
    return Path("email_verifier.db")
