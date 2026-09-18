#!/usr/bin/env python3
"""Prepare an unscored ChatGPT/product pilot. Never fabricate participant results."""
import hashlib
import json
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/product_validation'

def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    corpus = ROOT / 'data/sggs.jsonl'
    rows = read_rows(corpus)
    groups = OrderedDict()
    for row in rows:
        groups.setdefault(row['context']['shabad_id'], []).append(row)
    exports = {}
    for variant in ['english', 'multilingual']:
        path = OUT / f'sggs_{variant}.txt'
        with path.open('w', encoding='utf-8') as f:
            f.write('Sri Guru Granth Sahib — ShabadOS database 4.8.7\nEnglish translation: Dr. Sant Singh Khalsa\nSource: https://github.com/shabados/database/releases/tag/4.8.7\nComplete local corpus, in source order. Shabad boundaries and source IDs are retained.\n\n')
            for sid, lines in groups.items():
                f.write(f'=== SHABAD {sid} ===\n')
                for line in lines:
                    c = line['citation']
                    f.write(f"[{line['verse_id']}; Ang {c['ang']}; author {c['author']}; raag {c['raag']}]\n")
                    if variant == 'multilingual':
                        f.write(line['gurmukhi'] + '\n' + line['transliteration'] + '\n')
                    f.write(line['translation'] + '\n')
                f.write('\n')
        exports[path.name] = {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    known = read_rows(ROOT / 'data/eval/sggs_known_item_v1.jsonl')
    concepts = read_rows(ROOT / 'data/eval/sggs_conceptual_review_v1.jsonl')
    tasks = []
    # Deliberately fixed pilot sample, not a held-out accuracy benchmark.
    for i in [0, 1, 2, 30, 31, 32]:
        row = known[i]
        tasks.append({'id': row['id'], 'kind': 'remembered_wording', 'query': row['query'],
                      'instruction': 'Find the source passage containing this wording. Give its Shabad ID and Ang, and inspect the complete passage.',
                      'provenance': 'mechanical_source_excerpt_existing_development_set',
                      'language': row['language']})
    for i in [0, 2, 4, 8, 12, 17]:
        row = concepts[i]
        tasks.append({'id': row['id'], 'kind': 'conceptual_discovery', 'query': row['query'],
                      'instruction': 'Find up to three relevant passages. Give their Shabad IDs and Angs, explain relevance briefly, and inspect the complete context of the best match.',
                      'provenance': 'assistant_authored_existing_development_set', 'language': row['language']})
    (OUT / 'pilot_tasks.jsonl').write_text(''.join(json.dumps(t, ensure_ascii=False)+'\n' for t in tasks))
    prompts = ['# ChatGPT pilot prompts', '', 'Upload ONE complete source export. Use a fresh chat for each task. Record the visible model and mode. Do not include answer keys or project rankings.', '']
    for t in tasks:
        prompts += [f"## {t['id']}", '', 'Using only the attached source file, complete this task. You may search the file or use available data-analysis tools. Do not use the web. If you cannot find support, say so; do not invent a source.', '', t['instruction'], '', t['query'], '']
    (OUT / 'CHATGPT_PROMPTS.md').write_text('\n'.join(prompts))
    manifest = {'status': 'prepared_not_executed', 'source_lines': len(rows), 'passages': len(groups),
                'corpus_sha256': hashlib.sha256(corpus.read_bytes()).hexdigest(), 'exports': exports,
                'pilot_tasks': len(tasks), 'human_participants': 0, 'chatgpt_runs': 0,
                'warning': 'Synthetic development pilot. No product superiority or user validation established.'}
    manifest_path = OUT / 'manifest.json'
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        # Preserve observed run status when regenerating source exports.
        manifest.update({key: value for key, value in previous.items()
                         if key not in {'source_lines', 'passages', 'corpus_sha256', 'exports', 'pilot_tasks'}})
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
