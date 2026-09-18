#!/usr/bin/env python3
"""Run tests without network access, credentials, or writes to user indexes."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    os.chdir(ROOT)
    with tempfile.TemporaryDirectory(prefix='gurbani-tests-') as directory:
        config = {'OPENAI_API_KEY': '', 'PYTHON_DOTENV_DISABLED': '1'}
        for variable, name in [('SEARCH_INDEX_PATH', 'search.sqlite'),
                               ('GITA_SEARCH_INDEX_PATH', 'gita-search.sqlite'),
                               ('FEEDBACK_DB_PATH', 'feedback.sqlite')]:
            target = Path(directory) / name
            if variable != 'FEEDBACK_DB_PATH' and (ROOT / 'data' / name).exists():
                shutil.copy2(ROOT / 'data' / name, target)
            config[variable] = str(target)
        with patch.dict(os.environ, config), patch(
            'socket.socket.connect', side_effect=RuntimeError('Network disabled in offline tests')
        ), patch('socket.create_connection', side_effect=RuntimeError('Network disabled in offline tests')):
            suite = unittest.defaultTestLoader.discover('tests')
            result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
