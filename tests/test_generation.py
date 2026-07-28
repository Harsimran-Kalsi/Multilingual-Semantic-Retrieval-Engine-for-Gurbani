import unittest

from backend.app.generation import GroundedAnswerGenerator
from backend.app.retrieval import CorpusRetriever
from backend.app.schemas import GroundedAnswer, GroundedStatement, SearchRequest


class GroundingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = CorpusRetriever().search(
            SearchRequest(query="How can I overcome ego?", top_k=3)
        )

    def test_only_retrieved_source_ids_survive_validation(self) -> None:
        source_id = self.sources[0].citation.source_id
        answer = GroundedAnswer(
            summary="The retrieved passage addresses ego.",
            summary_citation_ids=[source_id, "invented-source"],
            statements=[
                GroundedStatement(
                    text="A grounded statement.",
                    citation_ids=[source_id, "invented-source"],
                )
            ],
        )
        validated = GroundedAnswerGenerator._validate_citations(answer, self.sources)
        self.assertEqual(validated.summary_citation_ids, [source_id])
        self.assertEqual(validated.statements[0].citation_ids, [source_id])

    def test_uncited_generated_answer_is_rejected(self) -> None:
        answer = GroundedAnswer(
            summary="An unsupported claim.",
            summary_citation_ids=["invented-source"],
            statements=[
                GroundedStatement(
                    text="Another unsupported claim.",
                    citation_ids=["invented-source"],
                )
            ],
        )
        with self.assertRaises(ValueError):
            GroundedAnswerGenerator._validate_citations(answer, self.sources)


if __name__ == "__main__":
    unittest.main()
