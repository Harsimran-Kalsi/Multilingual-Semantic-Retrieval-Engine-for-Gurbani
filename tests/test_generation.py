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

    def test_mixed_valid_and_invented_citations_reject_the_answer(self) -> None:
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
        with self.assertRaises(ValueError):
            GroundedAnswerGenerator._validate_citations(answer, self.sources)

    def test_valid_duplicate_citations_are_deduplicated(self) -> None:
        source_id = self.sources[0].citation.source_id
        answer = GroundedAnswer(summary='A cited summary.', summary_citation_ids=[source_id, source_id],
            statements=[GroundedStatement(text='A cited statement.', citation_ids=[source_id, source_id])])
        checked = GroundedAnswerGenerator._validate_citations(answer, self.sources)
        self.assertEqual(checked.summary_citation_ids, [source_id])
        self.assertEqual(checked.statements[0].citation_ids, [source_id])

    def test_uncited_statement_is_not_silently_dropped(self) -> None:
        source_id = self.sources[0].citation.source_id
        answer = GroundedAnswer(summary='Summary.', summary_citation_ids=[source_id], statements=[
            GroundedStatement(text='Cited.', citation_ids=[source_id]),
            GroundedStatement(text='Uncited.', citation_ids=[])])
        with self.assertRaises(ValueError):
            GroundedAnswerGenerator._validate_citations(answer, self.sources)

    def test_valid_id_does_not_prove_semantic_support(self) -> None:
        # Deliberately documents the boundary: reference validation is not an
        # entailment model. Never interpret passing it as hallucination-free.
        source_id = self.sources[0].citation.source_id
        answer = GroundedAnswer(summary='An unrelated factual claim.', summary_citation_ids=[source_id],
            statements=[GroundedStatement(text='Another unrelated claim.', citation_ids=[source_id])])
        self.assertEqual(GroundedAnswerGenerator._validate_citations(answer, self.sources), answer)

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
