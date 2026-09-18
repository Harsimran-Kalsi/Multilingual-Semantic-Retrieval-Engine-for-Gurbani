import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_known_item_eval import FIELDS, build, normalized
from scripts.evaluate_retrieval import load_cases


class EvaluationDataTests(unittest.TestCase):
    def test_checked_in_benchmark_has_balanced_explicit_provenance(self):
        cases = load_cases(Path('data/eval/sggs_known_item_v1.jsonl'))
        self.assertEqual(len(cases), 120)
        self.assertEqual({language: sum(c['language'] == language for c in cases) for language in FIELDS},
                         {'en': 40, 'pa-Latn': 40, 'pa-Guru': 40})
        self.assertEqual(len({c['provenance']['source_verse_id'] for c in cases}), 40)
        self.assertTrue(all(c['judgment_status'] == 'silver' and not c['provenance']['reviewed_by_human'] for c in cases))

    def test_realistic_question_pack_is_unjudged(self):
        cases = load_cases(Path('data/eval/sggs_conceptual_review_v1.jsonl'))
        self.assertEqual(len(cases), 30)
        self.assertTrue(all(c['judgment_status'] == 'unjudged' and 'relevant_shabad_ids' not in c for c in cases))

    def test_generator_is_reproducible_and_handles_duplicate_source_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'corpus.jsonl'
            phrase = 'one two three four five six seven eight'
            rows = [{'verse_id': f'v{i}', 'context': {'shabad_id': f's{i}'},
                'citation': {'source_id': f'source{i}'}, **{field: phrase for field in FIELDS.values()}}
                for i in range(3)]
            path.write_text('\n'.join(json.dumps(row) for row in rows))
            first, second = build(path, passages=2), build(path, passages=2)
            self.assertEqual(first, second)
            self.assertTrue(all(row['relevant_shabad_ids'] == ['s0', 's1', 's2'] for row in first))
