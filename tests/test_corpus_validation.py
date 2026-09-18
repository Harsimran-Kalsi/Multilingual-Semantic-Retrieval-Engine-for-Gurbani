from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CorpusValidationTests(unittest.TestCase):
    def test_invalid_corpus_fails_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.jsonl'
            path.write_text('{"verse_id":"incomplete"}\n')
            result = subprocess.run([sys.executable, 'scripts/prepare_corpus.py', '--input', str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Invalid records: 1', result.stdout)

    def test_valid_corpus_passes_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'valid.jsonl'
            with Path('data/sggs.jsonl').open() as source:
                path.write_text(source.readline())
            result = subprocess.run([sys.executable, 'scripts/prepare_corpus.py', '--input', str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
