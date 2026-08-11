import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.app.schemas import FeedbackRequest


class FeedbackStore:
    """Small local relevance-feedback store; no user identity is collected."""

    def __init__(self, database_path: Optional[str] = None) -> None:
        root = Path(__file__).resolve().parents[2]
        self.database_path = Path(
            database_path
            or os.getenv("FEEDBACK_DB_PATH")
            or root / "data" / "feedback.sqlite"
        )
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS relevance_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                query TEXT NOT NULL,
                verse_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                result_rank INTEGER NOT NULL,
                helpful INTEGER NOT NULL CHECK (helpful IN (0, 1)),
                sparse_score REAL,
                dense_score REAL,
                fusion_score REAL
            )
            """
        )
        columns = {
            row["name"] for row in connection.execute(
                "PRAGMA table_info(relevance_feedback)"
            )
        }
        if "fusion_score" not in columns:
            connection.execute(
                "ALTER TABLE relevance_feedback ADD COLUMN fusion_score REAL"
            )
            if "rerank_score" in columns:
                connection.execute(
                    "UPDATE relevance_feedback SET fusion_score = rerank_score "
                    "WHERE fusion_score IS NULL"
                )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS feedback_query_idx "
            "ON relevance_feedback(query)"
        )
        connection.commit()
        connection.close()

    def record(self, feedback: FeedbackRequest) -> int:
        connection = self._connect()
        cursor = connection.execute(
            """
            INSERT INTO relevance_feedback (
                created_at, query, verse_id, source_id, result_rank, helpful,
                sparse_score, dense_score, fusion_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                feedback.query.strip(),
                feedback.verse_id,
                feedback.source_id,
                feedback.result_rank,
                int(feedback.helpful),
                feedback.sparse_score,
                feedback.dense_score,
                feedback.fusion_score,
            ),
        )
        feedback_id = int(cursor.lastrowid)
        connection.commit()
        connection.close()
        return feedback_id

    def summary(self) -> dict:
        connection = self._connect()
        overall = connection.execute(
            """
            SELECT COUNT(*) AS total, COALESCE(SUM(helpful), 0) AS helpful
            FROM relevance_feedback
            """
        ).fetchone()
        by_rank = connection.execute(
            """
            SELECT result_rank, COUNT(*) AS total, SUM(helpful) AS helpful
            FROM relevance_feedback
            GROUP BY result_rank ORDER BY result_rank
            """
        ).fetchall()
        weak_queries = connection.execute(
            """
            SELECT query, COUNT(*) AS ratings,
                   ROUND(100.0 * SUM(helpful) / COUNT(*), 1) AS helpful_percent
            FROM relevance_feedback
            GROUP BY query
            HAVING COUNT(*) > 0
            ORDER BY helpful_percent ASC, ratings DESC, query
            LIMIT 20
            """
        ).fetchall()
        connection.close()
        total = int(overall["total"])
        helpful = int(overall["helpful"])
        return {
            "total": total,
            "helpful": helpful,
            "helpful_percent": round(100 * helpful / total, 1) if total else 0.0,
            "by_rank": [dict(row) for row in by_rank],
            "weak_queries": [dict(row) for row in weak_queries],
        }
