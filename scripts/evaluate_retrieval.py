#!/usr/bin/env python3
"""Evaluate current and legacy SGGS retrieval on a fixed JSONL judgment set."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.retrieval import CorpusRetriever
from backend.app.schemas import SearchRequest


def legacy_shabad_ranking(retriever: CorpusRetriever, query: str, limit: int) -> list[str]:
    lexical = retriever._lexical_ranking(query, {}, (4.0, 2.0, 2.5), limit=80)
    semantic = retriever._semantic_ranking(query, limit=80)
    fused: dict[str, float] = {}
    for ranking in (lexical, semantic):
        for rank, (shabad_id, _) in enumerate(ranking, start=1):
            fused[shabad_id] = fused.get(shabad_id, 0.0) + 1 / (retriever.RRF_K + rank)
    return sorted(fused, key=fused.get, reverse=True)[:limit]


def current_shabad_ranking(
    retriever: CorpusRetriever, query: str, language: str, limit: int
) -> list[str]:
    hint = {"pa-Guru": "pa-guru", "pa-Latn": "pa", "en": "en"}.get(language)
    results = retriever.search(
        SearchRequest(query=query, top_k=limit, language_hint=hint)
    )
    return [result.context.shabad_id for result in results if result.context]


def score(cases: list[dict], rankings: dict[str, list[str]]) -> dict:
    groups: dict[str, list[tuple[Optional[int], int]]] = defaultdict(list)
    for case in cases:
        relevant = set(case["relevant_shabad_ids"])
        rank = next(
            (index for index, item in enumerate(rankings[case["id"]], start=1) if item in relevant),
            None,
        )
        groups["all"].append((rank, len(rankings[case["id"]])))
        groups[case["language"]].append((rank, len(rankings[case["id"]])))
    report = {}
    for group, values in groups.items():
        report[group] = {
            "queries": len(values),
            "recall_at_1": sum(rank == 1 for rank, _ in values) / len(values),
            "recall_at_5": sum(rank is not None and rank <= 5 for rank, _ in values) / len(values),
            "recall_at_10": sum(rank is not None and rank <= 10 for rank, _ in values) / len(values),
            "mrr_at_10": sum(1 / rank for rank, _ in values if rank and rank <= 10) / len(values),
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--judgments", type=Path,
        default=Path("data/eval/sggs_retrieval_silver.jsonl"),
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.judgments.read_text(encoding="utf-8").splitlines() if line]
    retriever = CorpusRetriever()
    legacy = {
        case["id"]: legacy_shabad_ranking(retriever, case["query"], args.top_k)
        for case in cases
    }
    current = {
        case["id"]: current_shabad_ranking(
            retriever, case["query"], case["language"], args.top_k
        )
        for case in cases
    }
    report = {"judgment_set": str(args.judgments), "legacy": score(cases, legacy), "current": score(cases, current)}
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print(f"Judgments: {args.judgments} ({len(cases)} queries)")
    print("This silver set measures direct multilingual correspondence, not theological relevance.\n")
    for group in report["current"]:
        old, new = report["legacy"][group], report["current"][group]
        print(
            f"{group:8}  R@1 {old['recall_at_1']:.3f} -> {new['recall_at_1']:.3f}  "
            f"R@5 {old['recall_at_5']:.3f} -> {new['recall_at_5']:.3f}  "
            f"MRR@10 {old['mrr_at_10']:.3f} -> {new['mrr_at_10']:.3f}"
        )


if __name__ == "__main__":
    main()
