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

    def test_passage_returns_complete_shabad_context(self) -> None:
        results = self.search("truth")
        passage = self.retriever.passage(results[0].verse_id)
        self.assertTrue(passage)
        self.assertTrue(all(line.context is not None for line in passage))
        self.assertEqual(
            {line.context.shabad_id for line in passage},
            {results[0].context.shabad_id},
        )


if __name__ == "__main__":
    unittest.main()
