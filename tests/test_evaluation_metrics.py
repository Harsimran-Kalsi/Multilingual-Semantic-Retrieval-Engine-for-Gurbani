import json
import math
from pathlib import Path
import tempfile
import unittest

from scripts.evaluate_retrieval import load_cases, percentile, score


class EvaluationMetricTests(unittest.TestCase):
    def test_hit_rate_and_recall_are_distinct_for_multiple_targets(self):
        cases = [{'id': 'q', 'language': 'en', 'relevant_shabad_ids': ['a', 'b']}]
        metrics = score(cases, {'q': ['a', 'other']})['all']
        self.assertEqual(metrics['hit_at_1'], 1)
        self.assertEqual(metrics['recall_at_1'], .5)
        self.assertEqual(metrics['recall_at_5'], .5)

    def test_mrr_and_graded_ndcg_have_known_values(self):
        cases = [{'id': 'q', 'language': 'en', 'relevant_shabad_ids': ['a', 'b'],
                  'relevance_grades': {'a': 3, 'b': 1}}]
        metrics = score(cases, {'q': ['x', 'b', 'a']})['all']
        self.assertEqual(metrics['mrr_at_10'], .5)
        expected = (1 / math.log2(3) + 7 / math.log2(4)) / (7 + 1 / math.log2(3))
        self.assertAlmostEqual(metrics['ndcg_at_5'], expected)

    def test_duplicate_results_do_not_inflate_recall(self):
        cases = [{'id': 'q', 'language': 'en', 'relevant_shabad_ids': ['a', 'b']}]
        self.assertEqual(score(cases, {'q': ['a', 'a', 'a']})['all']['recall_at_5'], .5)

    def test_unjudged_questions_produce_no_quality_metrics(self):
        self.assertEqual(score([{'id': 'q', 'language': 'en'}], {'q': ['a']}), {})

    def test_percentile_interpolates_and_handles_empty_samples(self):
        self.assertEqual(percentile([10, 20], .5), 15)
        self.assertEqual(percentile([], .95), 0)

    def test_invalid_judgment_files_are_rejected(self):
        valid = {'id': 'q', 'query': 'truth', 'language': 'en', 'relevant_shabad_ids': ['a']}
        cases = [[valid, valid], [{**valid, 'relevant_shabad_ids': ['missing']}],
                 [{**valid, 'query': ' '}], [{**valid, 'judgment_status': 'unjudged'}],
                 [{**valid, 'relevance_grades': {'a': -1}}]]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cases.jsonl'
            for rows in cases:
                with self.subTest(rows=rows):
                    path.write_text('\n'.join(json.dumps(row) for row in rows))
                    with self.assertRaises(ValueError):
                        load_cases(path, {'a'})
