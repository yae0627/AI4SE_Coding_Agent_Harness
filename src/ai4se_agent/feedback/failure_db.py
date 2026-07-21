import sqlite3
from pathlib import Path


class FailureDB:
    def __init__(self, db_path: str = "memory/failure.db"):
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS failure_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    failure_type TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    fix_strategy TEXT,
                    count INTEGER DEFAULT 1,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def record_failure(self, failure_type: str, pattern: str, fix_strategy: str = "") -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                "INSERT INTO failure_patterns (failure_type, pattern, fix_strategy) VALUES (?, ?, ?)",
                (failure_type, pattern, fix_strategy)
            )
            conn.commit()
        finally:
            conn.close()

    def query_similar(self, failure_type: str) -> list[dict]:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM failure_patterns WHERE failure_type = ? ORDER BY count DESC LIMIT 5",
                (failure_type,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
