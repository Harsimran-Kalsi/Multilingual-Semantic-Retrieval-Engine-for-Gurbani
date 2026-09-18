#!/usr/bin/env python3
"""Reproducible retrieval comparison; offline by default, live hybrid opt-in."""
import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import sqlite3
import sys
import tempfile
import time
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.retrieval import CorpusRetriever
from backend.app.schemas import SearchRequest


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases(path: Path, known_ids: Optional[set[str]] = None) -> list[dict]:
    cases, seen = [], set()
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
            if not isinstance(case, dict):
                raise ValueError('row must be an object')
            if not isinstance(case.get('id'), str) or not case['id'].strip() or case['id'] in seen:
                raise ValueError('missing or duplicate query id')
            SearchRequest(query=case.get('query'), top_k=10)
            if case.get('language') not in {'en', 'pa-Latn', 'pa-Guru'}:
                raise ValueError('unsupported language')
            relevant = case.get('relevant_shabad_ids')
            if relevant is not None:
                if not isinstance(relevant, list) or not relevant or not all(isinstance(key, str) for key in relevant):
                    raise ValueError('judged queries need a nonempty list of relevant Shabad IDs')
                if len(set(relevant)) != len(relevant):
                    raise ValueError('duplicate relevant Shabad IDs')
                if known_ids is not None and set(relevant) - known_ids:
                    raise ValueError('unknown relevant Shabad ID')
            grades = case.get('relevance_grades')
            if grades is not None:
                if not isinstance(grades, dict) or relevant is None or set(grades) != set(relevant):
                    raise ValueError('grades must cover exactly the relevant Shabad IDs')
                if any(type(value) is not int or not 1 <= value <= 3 for value in grades.values()):
                    raise ValueError('positive relevance grades must be integers from 1 to 3')
            if case.get('judgment_status') == 'unjudged' and relevant is not None:
                raise ValueError('unjudged queries cannot contain ground-truth labels')
            cases.append(case)
            seen.add(case['id'])
        except (ValueError, TypeError) as exc:
            raise ValueError(f'{path.name}:{number}: {exc}') from exc
    if not cases:
        raise ValueError('Evaluation file has no queries')
    return cases


def legacy_shabad_ranking(retriever: CorpusRetriever, query: str, limit: int) -> list[str]:
    """Single combined-field BM25 baseline, always lexical (no implicit API calls)."""
    return [key for key, _ in retriever._lexical_ranking(query, {}, (4.0, 2.0, 2.5), limit=max(80, limit))][:limit]


def current_shabad_ranking(retriever: CorpusRetriever, query: str, language: Optional[str], limit: int,
                           mode: str = 'lexical') -> list[str]:
    hint = {'pa-Guru': 'pa-guru', 'pa-Latn': 'pa', 'en': 'en'}.get(language)
    return [result.context.shabad_id for result in retriever.search(
        SearchRequest(query=query, top_k=limit, language_hint=hint), mode=mode) if result.context]


def score(cases: list[dict], rankings: dict[str, list[str]]) -> dict:
    groups = defaultdict(list)
    for case in cases:
        relevant = set(case.get('relevant_shabad_ids') or [])
        if not relevant:
            continue
        ranking = list(dict.fromkeys(rankings.get(case['id'], [])))
        grades = case.get('relevance_grades') or {key: 1 for key in relevant}
        rank = next((i for i, key in enumerate(ranking[:10], 1) if key in relevant), None)
        row = {'mrr_at_10': 1 / rank if rank else 0.0}
        for k in (1, 5, 10):
            retrieved = ranking[:k]
            matches = len(set(retrieved) & relevant)
            row[f'hit_at_{k}'] = float(matches > 0)
            row[f'recall_at_{k}'] = matches / len(relevant)
            dcg = sum((2 ** grades.get(key, 0) - 1) / math.log2(i + 2) for i, key in enumerate(retrieved))
            ideal = sum((2 ** grade - 1) / math.log2(i + 2) for i, grade in enumerate(sorted(grades.values(), reverse=True)[:k]))
            row[f'ndcg_at_{k}'] = dcg / ideal if ideal else 0.0
        groups['all'].append(row)
        groups[case['language']].append(row)
    return {group: {'queries': len(rows), **{metric: sum(row[metric] for row in rows) / len(rows)
             for metric in rows[0]}} for group, rows in groups.items()}


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


@contextmanager
def isolated_retriever():
    """Never overwrite a working project's index during benchmarking."""
    source = Path(os.getenv('SEARCH_INDEX_PATH') or ROOT / 'data/search.sqlite').resolve()
    with tempfile.TemporaryDirectory(prefix='gurbani-eval-') as directory:
        target = Path(directory) / 'search.sqlite'
        if source.exists():
            with sqlite3.connect(f'{source.as_uri()}?mode=ro', uri=True) as original, sqlite3.connect(target) as copied:
                original.backup(copied)
        yield CorpusRetriever(index_path=str(target))


def review_pool(cases, rankings_by_system, retriever, seed):
    rows = []
    for case in cases:
        candidates = sorted({key for rankings in rankings_by_system.values() for key in rankings[case['id']]})
        rng = random.Random(f'{seed}:{case["id"]}')
        rng.shuffle(candidates)
        entries = []
        for key in candidates:
            line = retriever._choose_line(key, case['query'])
            entries.append({'shabad_id': key, 'verse_id': line['verse_id'],
                'source_id': line['citation']['source_id'], 'ang': line['citation']['ang'],
                'gurmukhi': line['gurmukhi'], 'translation': line.get('translation'),
                'context_endpoint': '/passage/' + line['verse_id'], 'relevance_grade': None})
        rows.append({'id': case['id'], 'query': case['query'], 'language': case['language'],
            'reviewer_id': None, 'reviewed_at': None, 'candidates': entries,
            'instructions': 'Read the complete passage before grading 0-3. Candidate order is shuffled; system identities hidden. Null means unjudged.'})
    return rows


def evaluate(retriever, cases, mode='lexical', repeats=3):
    functions = {'bm25': lambda case: legacy_shabad_ranking(retriever, case['query'], 10),
                 'multiview': lambda case: current_shabad_ranking(retriever, case['query'], None, 10)}
    if mode == 'hybrid':
        functions['hybrid'] = lambda case: current_shabad_ranking(retriever, case['query'], None, 10, mode='hybrid')
    systems, pools = {}, {}
    for name, function in functions.items():
        rankings, first_ms, warm_ms, statuses = {}, [], [], Counter()
        for case in cases:
            start = time.perf_counter()
            rankings[case['id']] = function(case)
            first_ms.append((time.perf_counter() - start) * 1000)
            if name == 'hybrid':
                statuses[retriever.search_diagnostics.get('semantic_status', 'unknown')] += 1
            for _ in range(repeats):
                start = time.perf_counter()
                function(case)
                warm_ms.append((time.perf_counter() - start) * 1000)
        systems[name] = {'metrics': score(cases, rankings), 'rankings': rankings,
            'semantic_status_counts': dict(statuses),
            'latency_ms': {'first_pass_p50': percentile(first_ms, .5), 'first_pass_p95': percentile(first_ms, .95),
                          'warm_p50': percentile(warm_ms, .5), 'warm_p95': percentile(warm_ms, .95),
                          'first_pass_samples': len(first_ms), 'warm_samples': len(warm_ms)}}
        pools[name] = rankings
    return systems, pools


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--judgments', type=Path, default=ROOT / 'data/eval/sggs_known_item_v1.jsonl')
    parser.add_argument('--mode', choices=['lexical', 'hybrid'], default='lexical',
        help='Hybrid makes live query-embedding API calls; lexical never does.')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--review-output', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.repeats <= 20:
        parser.error('--repeats must be between 0 and 20')
    if args.mode == 'hybrid':
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
    with isolated_retriever() as retriever:
        cases = load_cases(args.judgments, set(retriever.shabads))
        if args.mode == 'hybrid' and not retriever.semantic_search_available:
            parser.error('Hybrid evaluation requires compatible persisted embeddings and an API key')
        systems, pools = evaluate(retriever, cases, args.mode, args.repeats)
        report = {'created_at': datetime.now(timezone.utc).isoformat(),
            'requested_mode': args.mode, 'queries': len(cases),
            'judged_queries': sum(bool(case.get('relevant_shabad_ids')) for case in cases),
            'manifest': {'corpus_sha256': fingerprint(retriever.corpus_path),
                'query_set_sha256': fingerprint(args.judgments), 'query_set': args.judgments.name,
                'retrieval_code_sha256': fingerprint(ROOT / 'backend/app/retrieval.py'),
                'index_version': retriever.INDEX_VERSION, 'index_sha256': fingerprint(retriever.index_path),
                'source_lines': len(retriever.records), 'passages': len(retriever.shabads),
                'embedding_model': retriever.embedding_model, 'embedding_count': len(retriever._embedding_ids),
                'embedding_dimensions': int(retriever._embedding_matrix.shape[1]) if retriever._embedding_matrix is not None else None,
                'python': platform.python_version(), 'platform': platform.platform(),
                'language_hints': False, 'ranking_depth': 10,
                'judgment_status_counts': dict(Counter(case.get('judgment_status', 'legacy_silver') for case in cases)),
                'warm_repeats_per_query': args.repeats},
            'limitations': ['Silver exact-source correspondence is not conceptual relevance or human review.',
                'This is not an independently held-out human benchmark; do not describe it as search accuracy.',
                'Latency excludes startup, index loading, HTTP and answer generation; sequential local runs, no concurrent load.',
                'First-pass latency includes query embedding requests in hybrid mode; warm runs reuse successful query embeddings.',
                'Any hybrid query without semantic_status=ok fell back to lexical and must not count as a successful hybrid request.'],
            'systems': systems}
        if args.review_output:
            args.review_output.parent.mkdir(parents=True, exist_ok=True)
            args.review_output.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in review_pool(cases, pools, retriever, 20260918)))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f'{len(cases)} queries; {report["judged_queries"]} judged; requested mode={args.mode}')
        for name, system in systems.items():
            metrics = system['metrics'].get('all')
            if metrics:
                print(f'{name}: Hit@5={metrics["hit_at_5"]:.3f}; Recall@5={metrics["recall_at_5"]:.3f}; MRR@10={metrics["mrr_at_10"]:.3f}')
            else:
                print(f'{name}: UNJUDGED - rankings collected, no quality metrics computed')
            print(f'  warm p50/p95: {system["latency_ms"]["warm_p50"]:.2f}/{system["latency_ms"]["warm_p95"]:.2f} ms; semantic={system["semantic_status_counts"]}')
    if args.mode == 'hybrid' and systems['hybrid']['semantic_status_counts'].get('ok', 0) != len(cases):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
