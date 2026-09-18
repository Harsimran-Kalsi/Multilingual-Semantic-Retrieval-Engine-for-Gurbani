import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import main
from backend.app.schemas import GroundedAnswer, GroundedStatement


class ApiBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)

    def test_input_limits_and_whitespace(self):
        for endpoint, body in [('/search', {'query': '   '}),
                ('/search', {'query': 'x' * 1001}), ('/ask', {'question': '  '}),
                ('/ask', {'question': 'truth', 'previous_questions': ['x' * 1001]}),
                ('/search', {'query': 'truth', 'filters': {'unknown': 'value'}}),
                ('/search', {'query': 'truth', 'filters': {'ang': '0'}})]:
            with self.subTest(body=body):
                self.assertEqual(self.client.post(endpoint, json=body).status_code, 422)

    def test_search_to_passage_and_reader_workflow(self):
        response = self.client.post('/search', json={'query': '  truth  ', 'top_k': 3})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['normalized_query'], 'truth')
        self.assertEqual(data['retrieval_mode'], 'keyword')
        selected = data['results'][0]
        passage = self.client.get('/passage/' + selected['verse_id']).json()
        self.assertIn(selected['verse_id'], [line['verse_id'] for line in passage['lines']])
        self.assertEqual(self.client.get('/reader/' + selected['verse_id'] + '?before=101').status_code, 400)
        self.assertEqual(self.client.get('/passage/does-not-exist').status_code, 404)

    def test_wording_lookup_stays_lexical_even_with_credentials(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-test-placeholder'}), patch('openai.OpenAI') as provider:
            response = self.client.post('/search', json={'query': 'truth'})
        provider.assert_not_called()
        self.assertEqual(response.json()['requested_mode'], 'lexical')
        self.assertEqual(response.json()['retrieval_mode'], 'keyword')

    def test_requested_meaning_search_reports_lexical_fallback(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            response = self.client.post('/search', json={'query': 'truth', 'mode': 'hybrid'})
        self.assertEqual(response.json()['requested_mode'], 'hybrid')
        self.assertEqual(response.json()['retrieval_mode'], 'keyword')

    def test_generation_failure_returns_sources_without_provider_details(self):
        with patch.object(main.answer_generator, 'api_key', 'offline-test-placeholder'), patch.object(
            main.answer_generator, 'generate', side_effect=RuntimeError('private provider detail')
        ):
            response = self.client.post('/ask', json={'question': 'What is truth?'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['generated'])
        self.assertTrue(data['sources'])
        self.assertNotIn('private provider detail', str(data))

    def test_invalid_citation_generation_falls_back_to_sources(self):
        invalid = GroundedAnswer(summary='Unsupported.', summary_citation_ids=['fake'],
            statements=[GroundedStatement(text='Unsupported.', citation_ids=['fake'])])
        def generate(**kwargs):
            return main.answer_generator._validate_citations(invalid, kwargs['sources'])
        with patch.object(main.answer_generator, 'generate', side_effect=generate):
            data = self.client.post('/ask', json={'question': 'What is truth?'}).json()
        self.assertFalse(data['generated'])
        self.assertTrue(data['sources'])

    def test_feedback_rejects_forged_source_and_records_valid_result(self):
        selected = self.client.post('/search', json={'query': 'truth'}).json()['results'][0]
        body = {'query': 'truth', 'verse_id': selected['verse_id'], 'source_id': 'forged',
                'result_rank': 1, 'helpful': True}
        self.assertEqual(self.client.post('/feedback', json=body).status_code, 400)
        body['source_id'] = selected['citation']['source_id']
        self.assertTrue(self.client.post('/feedback', json=body).json()['recorded'])
