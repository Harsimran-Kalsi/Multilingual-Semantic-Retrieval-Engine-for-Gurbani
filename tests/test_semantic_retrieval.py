import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from backend.app.retrieval import CorpusRetriever
from backend.app.schemas import SearchRequest


class SemanticRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-test-placeholder',
                                          'OPENAI_EMBEDDING_MODEL': 'test-embedding'})
        self.env.start()
        self.addCleanup(self.env.stop)
        records = []
        for verse, shabad, ang, translation in [('a1', 'a', 1, 'alpha truth'),
                ('a2', 'a', 2, 'beta compassion'), ('b1', 'b', 3, 'kindness service'),
                ('c1', 'c', 4, 'peace kindness')]:
            records.append({'verse_id': verse, 'gurmukhi': 'ਸਚੁ', 'translation': translation,
                'transliteration': translation, 'context': {'shabad_id': shabad},
                'citation': {'ang': ang, 'source_id': verse, 'author': 'Author', 'raag': 'Raag'}})
        corpus = Path(self.temp.name) / 'corpus.jsonl'
        corpus.write_text('\n'.join(json.dumps(row) for row in records))
        self.retriever = CorpusRetriever(str(corpus), str(Path(self.temp.name) / 'index.sqlite'))
        self.install_vectors([('a', [1., 0.]), ('b', [0., 1.]), ('c', [-1., 0.])])

    def install_vectors(self, rows, model='test-embedding'):
        connection = self.retriever._connect()
        connection.execute('DELETE FROM embeddings')
        for key, values in rows:
            vector = np.asarray(values, dtype=np.float32)
            connection.execute('INSERT INTO embeddings VALUES (?, ?, ?, ?)',
                (key, model, len(values), vector.tobytes()))
        connection.commit()
        connection.close()
        self.retriever._load_embeddings()

    def embedding_response(self, vector):
        return SimpleNamespace(data=[SimpleNamespace(embedding=vector, index=0)])

    def test_dense_ranking_uses_cosine_and_cache(self):
        with patch('openai.OpenAI') as client:
            client.return_value.embeddings.create.return_value = self.embedding_response([0., 7.])
            results = self.retriever.search(SearchRequest(mode='hybrid', query='unseen concept', top_k=2))
            self.assertEqual(results[0].context.shabad_id, 'b')
            self.assertAlmostEqual(results[0].dense_score, 1.0)
            self.assertIsNotNone(results[0].fusion_score)
            self.retriever.search(SearchRequest(mode='hybrid', query='unseen concept', top_k=2))
            client.return_value.embeddings.create.assert_called_once()
            self.assertTrue(self.retriever.search_diagnostics['query_embedding_cached'])

    def test_lexical_mode_never_calls_embedding_provider(self):
        with patch('openai.OpenAI') as client:
            self.assertTrue(self.retriever.search(SearchRequest(mode='hybrid', query='kindness'), mode='lexical'))
            client.assert_not_called()
            self.assertEqual(self.retriever.search_diagnostics['semantic_status'], 'disabled')

    def test_provider_failure_preserves_keyword_results(self):
        with patch('openai.OpenAI') as client:
            client.return_value.embeddings.create.side_effect = TimeoutError('simulated timeout')
            results = self.retriever.search(SearchRequest(mode='hybrid', query='kindness'))
            self.assertTrue(results)
            self.assertTrue(all(result.dense_score is None for result in results))
            self.assertEqual(self.retriever.search_diagnostics['semantic_status'], 'embedding_request_failed')

    def test_bad_query_vectors_fall_back_without_nan_scores(self):
        for vector in ([0., 0.], [float('nan'), 1.], [1., 2., 3.]):
            with self.subTest(vector=vector), patch('openai.OpenAI') as client:
                client.return_value.embeddings.create.return_value = self.embedding_response(vector)
                self.assertTrue(self.retriever.search(SearchRequest(mode='hybrid', query='kindness')))
                self.assertEqual(self.retriever.search_diagnostics['semantic_status'], 'invalid_query_vector')

    def test_index_from_different_model_is_not_used(self):
        self.install_vectors([('a', [1., 0.])], model='another-model')
        with patch('openai.OpenAI') as client:
            self.assertFalse(self.retriever.semantic_search_available)
            self.assertTrue(self.retriever.search(SearchRequest(mode='hybrid', query='truth')))
            client.assert_not_called()

    def test_invalid_persisted_vectors_are_excluded(self):
        self.install_vectors([('a', [0., 0.]), ('b', [float('nan'), 1.]), ('c', [1., 0.])])
        self.assertEqual(self.retriever._embedding_ids, ['c'])

    def test_embedding_batch_rejects_duplicate_response_indices(self):
        with patch('openai.OpenAI') as client:
            client.return_value.embeddings.create.return_value = SimpleNamespace(data=[
                SimpleNamespace(index=0, embedding=[1., 0.]), SimpleNamespace(index=0, embedding=[0., 1.])])
            with self.assertRaisesRegex(ValueError, 'requested batch'):
                self.retriever.build_embeddings(model='replacement-model', dimensions=2, batch_size=2)
        connection = self.retriever._connect()
        self.assertEqual(connection.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0], 3)
        connection.close()

    def test_ang_filter_finds_later_page_of_passage(self):
        results = self.retriever.search(SearchRequest(mode='hybrid', query='beta', filters={'ang': '2'}), mode='lexical')
        self.assertEqual([result.verse_id for result in results], ['a2'])

    def test_dense_results_choose_line_matching_ang_filter(self):
        with patch('openai.OpenAI') as client:
            client.return_value.embeddings.create.return_value = self.embedding_response([1., 0.])
            results = self.retriever.search(SearchRequest(mode='hybrid', query='unseen concept', filters={'ang': '2'}))
            self.assertEqual([result.verse_id for result in results], ['a2'])

    def test_dense_and_keyword_signals_both_reach_fusion(self):
        with patch('openai.OpenAI') as client:
            client.return_value.embeddings.create.return_value = self.embedding_response([0., 1.])
            results = self.retriever.search(SearchRequest(mode='hybrid', query='kindness'))
            self.assertTrue(any(r.dense_score is not None and r.sparse_score is not None for r in results))
            self.assertEqual(len(results), len({r.context.shabad_id for r in results}))
