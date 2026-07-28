import json
import math
import os
import re
from pathlib import Path
from typing import Any, Optional

from backend.app.schemas import SearchRequest, SearchResult, TranslationItem, VerseCitation

TOKEN_SPLIT_RE = re.compile(r"[^\w\u0A00-\u0A7F]+", flags=re.UNICODE)
GURMUKHI_RE = re.compile(r"[\u0A00-\u0A7F]")

QUERY_ALIASES = {
    "name": ["ਨਾਮ", "ਨਾਮੁ"],
    "naam": ["ਨਾਮ", "ਨਾਮੁ"],
    "god": ["ਹਰਿ", "ਪ੍ਰਭੁ", "ਵਾਹਿਗੁਰੂ"],
    "waheguru": ["ਵਾਹਿਗੁਰੂ"],
    "peace": ["ਸੁਖ", "ਸਹਜ", "ਸ਼ਾਂਤਿ"],
    "shanti": ["ਸ਼ਾਂਤਿ", "ਸੁਖ"],
    "sukh": ["ਸੁਖ"],
    "inner": ["ਮਨ"],
    "mind": ["ਮਨ"],
    "mann": ["ਮਨ"],
    "man": ["ਮਨ"],
    "ego": ["ਹਉਮੈ"],
    "haumai": ["ਹਉਮੈ"],
    "truth": ["ਸਚੁ", "ਸਤਿ"],
    "sach": ["ਸਚੁ", "ਸਤਿ"],
    "hukam": ["ਹੁਕਮ", "ਹੁਕਮਿ", "ਹੁਕਮੇ"],
    "command": ["ਹੁਕਮ", "ਹੁਕਮਿ"],
    "service": ["ਸੇਵਾ"],
    "seva": ["ਸੇਵਾ"],
    "guru": ["ਗੁਰੁ", "ਸਤਿਗੁਰੁ"],
    "fear": ["ਨਿਰਭਉ"],
    "love": ["ਪ੍ਰੇਮ", "ਪਿਆਰ"],
    "prem": ["ਪ੍ਰੇਮ"],
    "remember": ["ਸਿਮਰਿ", "ਸਿਮਰਨ"],
    "meditate": ["ਸਿਮਰਿ", "ਧਿਆਇ"],
    "meditation": ["ਸਿਮਰਨ", "ਧਿਆਨ"],
    "simran": ["ਸਿਮਰਨ", "ਸਿਮਰਿ", "ਸਿਮਰਤ"],
    "simar": ["ਸਿਮਰਿ", "ਸਿਮਰਨ"],
    "grace": ["ਕਿਰਪਾ", "ਨਦਰਿ"],
    "kirpa": ["ਕਿਰਪਾ"],
    "death": ["ਮਰਣ", "ਮਰੈ"],
    "life": ["ਜੀਵਨ", "ਜੀਉ"],
    "soul": ["ਆਤਮ", "ਜੀਉ"],
}


def _normalize_text(text: Any) -> str:
    if text is None:
        return ""
    return " ".join(TOKEN_SPLIT_RE.split(str(text).lower())).strip()


def _token_set(text: str) -> set[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return set()
    return {tok for tok in normalized.split(" ") if tok}


def _query_variants(query: str) -> list[str]:
    """Return independent query forms so Latin text does not dilute Gurmukhi matches."""
    if GURMUKHI_RE.search(query):
        return [query]
    tokens = _token_set(query)
    variants = [query]
    for tok in tokens:
        variants.extend(QUERY_ALIASES.get(tok, []))
    return list(dict.fromkeys(variants))


def _char_ngrams(text: str, n: int = 3) -> dict[str, int]:
    normalized = _normalize_text(text).replace(" ", "")
    if not normalized:
        return {}
    if len(normalized) < n:
        return {normalized: 1}
    out: dict[str, int] = {}
    for i in range(len(normalized) - n + 1):
        gram = normalized[i : i + n]
        out[gram] = out.get(gram, 0) + 1
    return out


def _cosine_sim(left: dict[str, int], right: dict[str, int]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(left[k] * right.get(k, 0) for k in left)
    left_norm = math.sqrt(sum(v * v for v in left.values()))
    right_norm = math.sqrt(sum(v * v for v in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


class CorpusRetriever:
    """
    Lightweight corpus-backed retriever.
    Scoring is hybrid lexical + character n-gram similarity for MVP.
    """

    def __init__(self, corpus_path: Optional[str] = None):
        root = Path(__file__).resolve().parents[2]
        default = root / "data" / "sggs.jsonl"
        self.corpus_path = Path(corpus_path or os.getenv("CORPUS_PATH") or default)
        self.records = self._load_records()
        self.documents = [self._index_record(row) for row in self.records]

    @staticmethod
    def _index_record(row: dict[str, Any]) -> dict[str, Any]:
        fields = {
            "gurmukhi": row.get("gurmukhi", ""),
            "transliteration": row.get("transliteration", ""),
            "translation": row.get("translation", ""),
        }
        if not fields["translation"]:
            fields["translations"] = " ".join(
                t.get("text", "")
                for t in (row.get("translations") or [])
                if isinstance(t, dict) and t.get("text")
            )
        return {
            "row": row,
            "fields": fields,
            "tokens": {name: _token_set(content) for name, content in fields.items()},
            "grams": {name: _char_ngrams(content) for name, content in fields.items()},
            "normalized": [_normalize_text(value) for value in fields.values() if value],
        }

    def _load_records(self) -> list[dict[str, Any]]:
        if not self.corpus_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.corpus_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    records.append(row)
                except json.JSONDecodeError:
                    continue
        return records

    def _passes_filters(self, row: dict[str, Any], filters: dict[str, str]) -> bool:
        if not filters:
            return True

        citation = row.get("citation", {})
        for key, value in filters.items():
            if value is None:
                continue
            wanted = str(value).strip().lower()
            if not wanted:
                continue
            if key == "ang":
                if str(citation.get("ang", "")).lower() != wanted:
                    return False
                continue
            if key in {"raag", "author"}:
                if str(citation.get(key, "")).strip().lower() != wanted:
                    return False
                continue
            if str(row.get(key, "")).strip().lower() != wanted:
                return False
        return True

    def search(self, request: SearchRequest) -> list[SearchResult]:
        query_variants = _query_variants(request.query.strip())
        query_features = [
            (_token_set(query), _char_ngrams(query), _normalize_text(query))
            for query in query_variants
        ]

        scored: list[tuple[float, float, float, dict[str, Any], str]] = []
        for document in self.documents:
            row = document["row"]
            if not self._passes_filters(row, request.filters):
                continue

            fields = document["fields"]

            lexical_scores: dict[str, float] = {}
            dense_scores: dict[str, float] = {}
            for name, content in fields.items():
                lexical_scores[name] = max(
                    _jaccard(tokens, document["tokens"][name])
                    for tokens, _, _ in query_features
                )
                dense_scores[name] = max(
                    _cosine_sim(grams, document["grams"][name])
                    for _, grams, _ in query_features
                )

            sparse_score = max(lexical_scores.values())
            dense_score = max(dense_scores.values())
            rerank_score = 0.45 * sparse_score + 0.55 * dense_score

            gurmukhi_tokens = document["tokens"]["gurmukhi"]
            exact_match = any(
                variant and variant in field
                for _, _, variant in query_features
                for field in document["normalized"]
            )
            # Prefer a useful verse line over a heading or isolated one-word fragment.
            if len(gurmukhi_tokens) >= 4:
                rerank_score *= 1.08
            else:
                rerank_score *= 0.25
            if exact_match and len(gurmukhi_tokens) >= 4:
                rerank_score += 0.08
            rerank_score = min(rerank_score, 1.0)

            best_field = max(
                fields,
                key=lambda f: (lexical_scores[f], dense_scores[f]),
            )
            explanation = f"Best similarity against {best_field} field."

            if rerank_score > 0:
                scored.append((rerank_score, sparse_score, dense_score, row, explanation))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_hits = scored[: request.top_k]

        results: list[SearchResult] = []
        for rerank_score, sparse_score, dense_score, row, explanation in top_hits:
            citation = row.get("citation", {})
            if not citation.get("source_id") or not citation.get("ang"):
                continue
            results.append(
                SearchResult(
                    verse_id=row.get("verse_id", ""),
                    gurmukhi=row.get("gurmukhi", ""),
                    transliteration=row.get("transliteration"),
                    translation=row.get("translation"),
                    translations=[
                        TranslationItem(
                            lang=str(t.get("lang", "unknown")),
                            text=str(t.get("text", "")),
                            translator=t.get("translator"),
                        )
                        for t in (row.get("translations") or [])
                        if isinstance(t, dict) and t.get("text")
                    ],
                    citation=VerseCitation(
                        ang=int(citation["ang"]),
                        raag=citation.get("raag"),
                        author=citation.get("author"),
                        source_id=citation["source_id"],
                        line_start=citation.get("line_start"),
                        line_end=citation.get("line_end"),
                    ),
                    sparse_score=round(sparse_score, 4),
                    dense_score=round(dense_score, 4),
                    rerank_score=round(rerank_score, 4),
                    match_explanation=explanation,
                )
            )
        return results
