import json
import unittest
from pathlib import Path

from backend.app.retrieval import CorpusRetriever
from scripts.evaluate_retrieval import (
    current_shabad_ranking,
    legacy_shabad_ranking,
    score,
)


class RetrievalEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = [
            json.loads(line)
            for line in Path("data/eval/sggs_retrieval_silver.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        ]
        cls.retriever = CorpusRetriever()
        # Make this a deterministic lexical regression test. Dense-model
        # comparisons belong in explicit evaluation runs with a pinned model.
        cls.retriever._semantic_ranking = lambda query, limit=80: []

    def test_multiview_retrieval_beats_or_matches_legacy_by_language(self) -> None:
        legacy = {
            case["id"]: legacy_shabad_ranking(
                self.retriever, case["query"], 10
            )
            for case in self.cases
        }
        current = {
            case["id"]: current_shabad_ranking(
                self.retriever, case["query"], case["language"], 10
            )
            for case in self.cases
        }
        old_report, new_report = score(self.cases, legacy), score(self.cases, current)
        for language in ("en", "pa-Latn", "pa-Guru", "all"):
            self.assertGreaterEqual(
                new_report[language]["recall_at_5"],
                old_report[language]["recall_at_5"],
            )
            self.assertGreaterEqual(
                new_report[language]["mrr_at_10"],
                old_report[language]["mrr_at_10"],
            )
