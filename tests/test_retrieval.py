import unittest

from backend.app.retrieval import CorpusRetriever
from backend.app.schemas import SearchRequest


class RetrievalSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.retriever = CorpusRetriever()

    def search(self, query: str):
        return self.retriever.search(SearchRequest(query=query, top_k=3))

    def test_gurmukhi_query_returns_cited_results(self) -> None:
        results = self.search("ਸਚੁ")
        self.assertTrue(results)
        self.assertTrue(all(result.citation.ang > 0 for result in results))
        self.assertTrue(all(result.citation.source_id for result in results))

    def test_roman_punjabi_alias_is_supported(self) -> None:
        results = self.retriever.search(SearchRequest(query="simran", top_k=3))
        self.assertTrue(results)
        self.assertTrue(any("ਸਿਮਰ" in result.gurmukhi for result in results))

    def test_query_profile_does_not_misclassify_english_aliases(self) -> None:
        self.assertEqual(
            self.retriever._query_profile("How can I overcome ego and fear?"),
            "english",
        )
        self.assertEqual(self.retriever._query_profile("haumai"), "roman-punjabi")

    def test_passage_returns_complete_shabad_context(self) -> None:
        results = self.search("truth")
        passage = self.retriever.passage(results[0].verse_id)
        self.assertTrue(passage)
        self.assertTrue(all(line.context is not None for line in passage))
        self.assertEqual(
            {line.context.shabad_id for line in passage},
            {results[0].context.shabad_id},
        )

    def test_results_are_diverse_by_shabad(self) -> None:
        results = self.retriever.search(
            SearchRequest(query="How can I overcome ego?", top_k=8)
        )
        shabad_ids = [result.context.shabad_id for result in results]
        self.assertEqual(len(shabad_ids), len(set(shabad_ids)))

    def test_reader_window_follows_canonical_source_order(self) -> None:
        verse_id = self.retriever.records[100]["verse_id"]
        lines, has_before, has_after = self.retriever.reader_window(
            verse_id, before=2, after=3
        )
        self.assertEqual(len(lines), 6)
        self.assertEqual(lines[2].verse_id, verse_id)
        self.assertTrue(has_before)
        self.assertTrue(has_after)

    def test_service_query_prioritizes_service_passages(self) -> None:
        results = self.retriever.search(
            SearchRequest(query="What does Gurbani say about serving others?", top_k=3)
        )
        translations = " ".join(result.translation or "" for result in results).lower()
        self.assertTrue("seva" in translations or "serv" in translations)


if __name__ == "__main__":
    unittest.main()
