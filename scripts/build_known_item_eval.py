#!/usr/bin/env python3
"""Build mechanically labelled source-lookup queries; never human relevance labels."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {'en': 'translation', 'pa-Latn': 'transliteration', 'pa-Guru': 'gurmukhi'}


def normalized(value):
    return ' '.join(str(value or '').casefold().split())


def build(corpus_path: Path, seed: int = 20260918, passages: int = 40) -> list[dict]:
    corpus = [json.loads(line) for line in corpus_path.read_text().splitlines() if line.strip()]
    groups = defaultdict(list)
    for row in corpus:
        groups[row['context']['shabad_id']].append(row)
    eligible = []
    for key, rows in groups.items():
        choices = [row for row in rows if all(len(str(row.get(field) or '').split()) >= 8 for field in FIELDS.values())]
        if choices:
            eligible.append((key, choices))
    if not 1 <= passages <= len(eligible):
        raise ValueError('Requested passage count exceeds eligible source passages')
    rng = random.Random(seed)
    selected = [rng.choice(eligible[i * len(eligible) // passages:(i + 1) * len(eligible) // passages])
                for i in range(passages)]
    fingerprint = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    cases = []
    for i, (key, choices) in enumerate(selected):
        row = rng.choice(choices)
        for language, field in FIELDS.items():
            words = str(row[field]).split()
            start = rng.randrange(len(words) - 7)
            query = ' '.join(words[start:start + 8])
            needle = normalized(query)
            relevant = sorted({record['context']['shabad_id'] for record in corpus
                               if needle in normalized(record.get(field))})
            cases.append({'id': f'known-{i + 1:03d}-{language}', 'language': language,
                'query': query, 'relevant_shabad_ids': relevant,
                'judgment_status': 'silver', 'task': 'known_item_lookup',
                'provenance': {'method': 'mechanical_exact_source_excerpt', 'seed': seed,
                    'source_field': field, 'source_verse_id': row['verse_id'],
                    'source_id': row['citation']['source_id'], 'corpus_sha256': fingerprint,
                    'sampling': 'one passage per equal-sized stratum in canonical corpus order',
                    'reviewed_by_human': False}})
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, default=ROOT / 'data/sggs.jsonl')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/eval/sggs_known_item_v1.jsonl')
    parser.add_argument('--seed', type=int, default=20260918)
    parser.add_argument('--passages', type=int, default=40)
    args = parser.parse_args()
    cases = build(args.corpus, args.seed, args.passages)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(''.join(json.dumps(case, ensure_ascii=False, sort_keys=True) + '\n' for case in cases))
    print(f'Wrote {len(cases)} mechanically labelled queries from {args.passages} sampled passages.')


if __name__ == '__main__':
    main()
