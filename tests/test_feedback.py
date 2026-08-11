import tempfile
import unittest
import sqlite3
from pathlib import Path

from backend.app.feedback import FeedbackStore
from backend.app.schemas import FeedbackRequest


class FeedbackStoreTests(unittest.TestCase):
    def test_record_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = FeedbackStore(str(Path(directory) / "feedback.sqlite"))
            store.record(
                FeedbackRequest(
                    query="How can I overcome ego?",
                    verse_id="shabados:test",
                    source_id="shabados:test:line",
                    result_rank=1,
                    helpful=True,
                    sparse_score=2.4,
                    dense_score=0.7,
                    fusion_score=0.03,
                )
            )
            summary = store.summary()
            self.assertEqual(summary["total"], 1)
            self.assertEqual(summary["helpful"], 1)
            self.assertEqual(summary["helpful_percent"], 100.0)
            self.assertEqual(summary["by_rank"][0]["result_rank"], 1)

    def test_legacy_rerank_score_is_migrated_to_fusion_score(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feedback.sqlite"
            connection = sqlite3.connect(path)
            connection.execute(
                """CREATE TABLE relevance_feedback (
                    id INTEGER PRIMARY KEY, created_at TEXT, query TEXT,
                    verse_id TEXT, source_id TEXT, result_rank INTEGER,
                    helpful INTEGER, sparse_score REAL, dense_score REAL,
                    rerank_score REAL
                )"""
            )
            connection.execute(
                "INSERT INTO relevance_feedback VALUES (1, '', 'q', 'v', 's', 1, 1, 1, 1, 0.25)"
            )
            connection.commit()
            connection.close()
            FeedbackStore(str(path))
            connection = sqlite3.connect(path)
            value = connection.execute(
                "SELECT fusion_score FROM relevance_feedback WHERE id=1"
            ).fetchone()[0]
            connection.close()
            self.assertEqual(value, 0.25)


if __name__ == "__main__":
    unittest.main()
