import json
import os
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from backend.app.schemas import (
    SearchRequest,
    SearchResult,
    TranslationItem,
    VerseCitation,
    VerseContext,
)

TOKEN_SPLIT_RE = re.compile(r"[^\w\u0A00-\u0A7F]+", flags=re.UNICODE)
GURMUKHI_RE = re.compile(r"[\u0A00-\u0A7F]")
ENGLISH_STOPWORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "been", "being",
    "but", "by", "can", "could", "did", "do", "does", "for", "from", "had",
    "has", "have", "he", "her", "him", "his", "how", "i", "if", "in", "into",
    "is", "it", "its", "me", "my", "of", "on", "or", "other", "others", "our",
    "said", "say", "says", "she", "should",
    "so", "than", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "those", "to", "us", "was", "we", "were", "what", "when",
    "where", "which", "who", "why", "will", "with", "would", "you", "your",
}

# Small, explicit cross-language expansions complement rather than replace semantic search.
QUERY_ALIASES = {
    "name": ["naam", "ਨਾਮ", "ਨਾਮੁ"],
    "naam": ["name", "ਨਾਮ", "ਨਾਮੁ"],
    "god": ["lord", "divine", "creator", "ਹਰਿ", "ਪ੍ਰਭੁ"],
    "waheguru": ["god", "ਵਾਹਿਗੁਰੂ"],
    "peace": ["peaceful", "ਸੁਖ", "ਸਹਜ", "ਸ਼ਾਂਤਿ"],
    "mind": ["inner", "ਮਨ"],
    "ego": ["pride", "haumai", "ਹਉਮੈ"],
    "haumai": ["ego", "pride", "ਹਉਮੈ"],
    "truth": ["true", "sach", "ਸਚੁ", "ਸਤਿ"],
    "sach": ["truth", "ਸਚੁ", "ਸਤਿ"],
    "hukam": ["command", "will", "ਹੁਕਮ", "ਹੁਕਮਿ", "ਹੁਕਮੇ"],
    "service": ["serve", "serving", "seva", "ਸੇਵਾ"],
    "serve": ["service", "seva", "ਸੇਵਾ"],
    "serving": ["service", "serve", "seva", "ਸੇਵਾ"],
    "seva": ["service", "serve", "ਸੇਵਾ"],
    "guru": ["ਗੁਰੁ", "ਸਤਿਗੁਰੁ"],
    "fear": ["afraid", "fearless", "ਨਿਰਭਉ"],
    "love": ["loving", "ਪ੍ਰੇਮ", "ਪਿਆਰ"],
    "prem": ["love", "ਪ੍ਰੇਮ"],
    "remember": ["remembrance", "simran", "ਸਿਮਰਿ", "ਸਿਮਰਨ"],
    "meditate": ["meditation", "simran", "ਸਿਮਰਿ", "ਧਿਆਇ"],
    "meditation": ["meditate", "simran", "ਸਿਮਰਨ", "ਧਿਆਨ"],
    "simran": ["remember", "meditate", "ਸਿਮਰਨ", "ਸਿਮਰਿ", "ਸਿਮਰਤ"],
    "grace": ["mercy", "kirpa", "ਕਿਰਪਾ", "ਨਦਰਿ"],
    "death": ["die", "dying", "ਮਰਣ", "ਮਰੈ"],
    "life": ["living", "ਜੀਵਨ", "ਜੀਉ"],
    "soul": ["spirit", "ਆਤਮ", "ਜੀਉ"],
}


def _normalize_text(text: Any) -> str:
    if text is None:
        return ""
    return " ".join(TOKEN_SPLIT_RE.split(str(text).lower())).strip()


def _tokens(text: str, remove_stopwords: bool = False) -> list[str]:
    values = [token for token in _normalize_text(text).split() if token]
    if remove_stopwords:
        meaningful = [token for token in values if token not in ENGLISH_STOPWORDS]
        return meaningful or values
    return values


def _expanded_terms(query: str) -> list[str]:
    terms = _tokens(query, remove_stopwords=not GURMUKHI_RE.search(query))
    expanded = list(terms)
    for term in terms:
        expanded.extend(QUERY_ALIASES.get(term, []))
    return list(dict.fromkeys(term for term in expanded if term))


def _fts_term(term: str) -> str:
    return '"' + term.replace('"', '""') + '"'


class CorpusRetriever:
    """Shabad-level BM25 + optional embedding retrieval with RRF fusion."""

    INDEX_VERSION = "2"
    RRF_K = 60

    def __init__(
        self,
        corpus_path: Optional[str] = None,
        index_path: Optional[str] = None,
    ):
        root = Path(__file__).resolve().parents[2]
        self.corpus_path = Path(
            corpus_path or os.getenv("CORPUS_PATH") or root / "data" / "sggs.jsonl"
        )
        self.index_path = Path(
            index_path or os.getenv("SEARCH_INDEX_PATH") or root / "data" / "search.sqlite"
        )
        self.records = self._load_records()
        self.records_by_id = {row.get("verse_id"): row for row in self.records}
        self.shabads: dict[str, list[dict[str, Any]]] = {}
        for row in self.records:
            shabad_id = str((row.get("context") or {}).get("shabad_id") or "")
            if shabad_id:
                self.shabads.setdefault(shabad_id, []).append(row)
        self._index_lock = threading.Lock()
        self._ensure_index()
        self._embedding_ids: list[str] = []
        self._embedding_matrix: Any = None
        self._query_embedding_cache: dict[str, Any] = {}
        self._load_embeddings()

    def _load_records(self) -> list[dict[str, Any]]:
        if not self.corpus_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.corpus_path.open("r", encoding="utf-8") as source:
            for line in source:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.index_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _index_is_current(self, connection: sqlite3.Connection) -> bool:
        try:
            values = dict(connection.execute("SELECT key, value FROM index_meta"))
            stat = self.corpus_path.stat()
            return (
                values.get("version") == self.INDEX_VERSION
                and values.get("corpus_size") == str(stat.st_size)
                and values.get("corpus_mtime_ns") == str(stat.st_mtime_ns)
                and values.get("shabad_count") == str(len(self.shabads))
            )
        except sqlite3.Error:
            return False

    def _ensure_index(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with self._index_lock:
            connection = self._connect()
            if self._index_is_current(connection):
                connection.close()
                return
            connection.executescript(
                """
                DROP TABLE IF EXISTS shabad_fts;
                DROP TABLE IF EXISTS shabad_meta;
                DROP TABLE IF EXISTS embeddings;
                DROP TABLE IF EXISTS index_meta;
                CREATE TABLE index_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE shabad_meta (
                    shabad_id TEXT PRIMARY KEY,
                    author TEXT,
                    raag TEXT,
                    first_ang INTEGER
                );
                CREATE VIRTUAL TABLE shabad_fts USING fts5(
                    shabad_id UNINDEXED,
                    translation,
                    transliteration,
                    gurmukhi,
                    tokenize='unicode61 remove_diacritics 0'
                );
                CREATE TABLE embeddings (
                    shabad_id TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    dimensions INTEGER NOT NULL,
                    vector BLOB NOT NULL
                );
                """
            )
            fts_rows = []
            meta_rows = []
            for shabad_id, rows in self.shabads.items():
                citation = rows[0].get("citation") or {}
                fts_rows.append(
                    (
                        shabad_id,
                        "\n".join(str(row.get("translation") or "") for row in rows),
                        "\n".join(str(row.get("transliteration") or "") for row in rows),
                        "\n".join(str(row.get("gurmukhi") or "") for row in rows),
                    )
                )
                meta_rows.append(
                    (
                        shabad_id,
                        citation.get("author"),
                        citation.get("raag"),
                        citation.get("ang"),
                    )
                )
            connection.executemany(
                "INSERT INTO shabad_fts VALUES (?, ?, ?, ?)", fts_rows
            )
            connection.executemany(
                "INSERT INTO shabad_meta VALUES (?, ?, ?, ?)", meta_rows
            )
            stat = self.corpus_path.stat()
            connection.executemany(
                "INSERT INTO index_meta VALUES (?, ?)",
                [
                    ("version", self.INDEX_VERSION),
                    ("corpus_size", str(stat.st_size)),
                    ("corpus_mtime_ns", str(stat.st_mtime_ns)),
                    ("shabad_count", str(len(self.shabads))),
                ],
            )
            connection.commit()
            connection.close()

    def _load_embeddings(self) -> None:
        try:
            import numpy as np
        except ImportError:
            return
        connection = self._connect()
        rows = connection.execute(
            "SELECT shabad_id, dimensions, vector FROM embeddings ORDER BY shabad_id"
        ).fetchall()
        connection.close()
        if not rows:
            return
        dimensions = int(rows[0]["dimensions"])
        valid_rows = [
            row for row in rows
            if int(row["dimensions"]) == dimensions
            and len(row["vector"]) == dimensions * 4
        ]
        if not valid_rows:
            return
        self._embedding_ids = [str(row["shabad_id"]) for row in valid_rows]
        self._embedding_matrix = np.vstack(
            [np.frombuffer(row["vector"], dtype=np.float32) for row in valid_rows]
        )

    @property
    def semantic_search_available(self) -> bool:
        return self._embedding_matrix is not None and bool(os.getenv("OPENAI_API_KEY"))

    @staticmethod
    def _embedding_text(rows: list[dict[str, Any]]) -> str:
        first = rows[0]
        citation = first.get("citation") or {}
        text = "\n".join(
            [
                f"Author: {citation.get('author') or ''}",
                f"Raag or section: {citation.get('raag') or ''}",
                "English translation:",
                *[str(row.get("translation") or "") for row in rows],
                "Gurmukhi:",
                *[str(row.get("gurmukhi") or "") for row in rows],
            ]
        )
        # The longest SGGS compositions exceed the embedding endpoint's 8,192
        # token input limit. Preserve balanced context from both ends.
        # Gurmukhi can tokenize more densely than English, so use a conservative
        # character ceiling without adding another tokenizer dependency.
        max_chars = 5_000
        if len(text) > max_chars:
            half = max_chars // 2
            text = text[:half] + "\n[...middle omitted...]\n" + text[-half:]
        return text

    def build_embeddings(
        self,
        model: str = "text-embedding-3-small",
        dimensions: int = 768,
        batch_size: int = 32,
    ) -> int:
        """Build missing persistent Shabad embeddings. Returns rows added."""
        from openai import OpenAI
        import numpy as np

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Set OPENAI_API_KEY before building embeddings.")
        connection = self._connect()
        existing = {
            str(row[0])
            for row in connection.execute(
                "SELECT shabad_id FROM embeddings WHERE model=? AND dimensions=?",
                (model, dimensions),
            )
        }
        pending = [
            (shabad_id, self._embedding_text(rows))
            for shabad_id, rows in self.shabads.items()
            if shabad_id not in existing
        ]
        client = OpenAI(api_key=api_key)
        added = 0
        for start in range(0, len(pending), batch_size):
            batch = pending[start : start + batch_size]
            response = client.embeddings.create(
                model=model,
                dimensions=dimensions,
                input=[text for _, text in batch],
                encoding_format="float",
            )
            db_rows = []
            for (shabad_id, _), item in zip(batch, response.data):
                vector = np.asarray(item.embedding, dtype=np.float32)
                norm = float(np.linalg.norm(vector))
                if norm:
                    vector /= norm
                db_rows.append(
                    (shabad_id, model, dimensions, vector.tobytes())
                )
            connection.executemany(
                """
                INSERT OR REPLACE INTO embeddings
                (shabad_id, model, dimensions, vector) VALUES (?, ?, ?, ?)
                """,
                db_rows,
            )
            connection.commit()
            added += len(db_rows)
            print(f"Embedded {added}/{len(pending)} Shabads", flush=True)
        connection.close()
        self._load_embeddings()
        return added

    def _passes_filters(self, row: dict[str, Any], filters: dict[str, str]) -> bool:
        citation = row.get("citation") or {}
        for key, value in filters.items():
            wanted = str(value or "").strip().lower()
            if not wanted:
                continue
            actual = citation.get(key) if key in {"ang", "raag", "author"} else row.get(key)
            if str(actual or "").strip().lower() != wanted:
                return False
        return True

    def _lexical_ranking(
        self, query: str, filters: dict[str, str], limit: int = 80
    ) -> list[tuple[str, float]]:
        terms = _expanded_terms(query)
        if not terms:
            return []
        match = " OR ".join(_fts_term(term) for term in terms)
        where = ["shabad_fts MATCH ?"]
        params: list[Any] = [match]
        for key, column in (("author", "author"), ("raag", "raag"), ("ang", "first_ang")):
            value = str(filters.get(key, "")).strip()
            if value:
                where.append(f"LOWER(CAST(m.{column} AS TEXT)) = LOWER(?)")
                params.append(value)
        params.append(limit)
        connection = self._connect()
        rows = connection.execute(
            f"""
            SELECT f.shabad_id, bm25(shabad_fts, 0.0, 4.0, 2.0, 2.5) AS score
            FROM shabad_fts f
            JOIN shabad_meta m ON m.shabad_id = f.shabad_id
            WHERE {' AND '.join(where)}
            ORDER BY score
            LIMIT ?
            """,
            params,
        ).fetchall()
        connection.close()
        return [(str(row["shabad_id"]), float(-row["score"])) for row in rows]

    def _semantic_ranking(self, query: str, limit: int = 80) -> list[tuple[str, float]]:
        if not self.semantic_search_available:
            return []
        import numpy as np
        from openai import OpenAI

        cache_key = _normalize_text(query)
        query_vector = self._query_embedding_cache.get(cache_key)
        if query_vector is None:
            try:
                model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
                dimensions = int(self._embedding_matrix.shape[1])
                response = OpenAI(api_key=os.environ["OPENAI_API_KEY"]).embeddings.create(
                    model=model,
                    dimensions=dimensions,
                    input=query.strip(),
                    encoding_format="float",
                )
                query_vector = np.asarray(response.data[0].embedding, dtype=np.float32)
                norm = float(np.linalg.norm(query_vector))
                if norm:
                    query_vector /= norm
                if len(self._query_embedding_cache) >= 256:
                    self._query_embedding_cache.pop(next(iter(self._query_embedding_cache)))
                self._query_embedding_cache[cache_key] = query_vector
            except Exception:
                # Search remains available through local BM25 during API/network issues.
                return []
        similarities = np.einsum("ij,j->i", self._embedding_matrix, query_vector)
        count = min(limit, len(similarities))
        indices = np.argpartition(-similarities, count - 1)[:count]
        indices = indices[np.argsort(-similarities[indices])]
        return [
            (self._embedding_ids[int(index)], float(similarities[int(index)]))
            for index in indices
        ]

    def _choose_line(self, shabad_id: str, query: str) -> dict[str, Any]:
        rows = self.shabads[shabad_id]
        query_terms = set(_expanded_terms(query))

        def score(row: dict[str, Any]) -> tuple[float, int]:
            text = " ".join(
                str(row.get(field) or "")
                for field in ("translation", "transliteration", "gurmukhi")
            )
            line_terms = set(_tokens(text))
            overlap = len(query_terms & line_terms) / max(1, len(query_terms))
            substantive = min(len(_tokens(str(row.get("gurmukhi") or ""))), 12) / 12
            return overlap + 0.08 * substantive, len(line_terms)

        return max(rows, key=score)

    @staticmethod
    def _to_result(
        row: dict[str, Any],
        explanation: str,
        sparse_score: Optional[float] = None,
        dense_score: Optional[float] = None,
        rerank_score: Optional[float] = None,
    ) -> SearchResult:
        citation = row.get("citation") or {}
        context = row.get("context")
        return SearchResult(
            verse_id=row.get("verse_id", ""),
            gurmukhi=row.get("gurmukhi", ""),
            transliteration=row.get("transliteration"),
            translation=row.get("translation"),
            translations=[
                TranslationItem(
                    lang=str(item.get("lang", "unknown")),
                    text=str(item.get("text", "")),
                    translator=item.get("translator"),
                )
                for item in (row.get("translations") or [])
                if isinstance(item, dict) and item.get("text")
            ],
            context=VerseContext(**context) if context else None,
            citation=VerseCitation(
                ang=int(citation["ang"]),
                raag=citation.get("raag"),
                author=citation.get("author"),
                source_id=citation["source_id"],
                line_start=citation.get("line_start"),
                line_end=citation.get("line_end"),
            ),
            sparse_score=round(sparse_score, 4) if sparse_score is not None else None,
            dense_score=round(dense_score, 4) if dense_score is not None else None,
            rerank_score=round(rerank_score, 4) if rerank_score is not None else None,
            match_explanation=explanation,
        )

    def passage(self, verse_id: str) -> list[SearchResult]:
        selected = self.records_by_id.get(verse_id)
        if not selected:
            return []
        shabad_id = str((selected.get("context") or {}).get("shabad_id") or "")
        return [
            self._to_result(row, "Part of the same Shabad passage.")
            for row in self.shabads.get(shabad_id, [selected])
            if (row.get("citation") or {}).get("source_id")
        ]

    def search(self, request: SearchRequest) -> list[SearchResult]:
        query = request.query.strip()
        lexical = self._lexical_ranking(query, request.filters)
        semantic = self._semantic_ranking(query)
        lexical_scores = dict(lexical)
        semantic_scores = dict(semantic)

        # RRF combines ranks rather than incomparable BM25 and cosine score scales.
        fused: dict[str, float] = {}
        for ranking in (lexical, semantic):
            for rank, (shabad_id, _) in enumerate(ranking, start=1):
                fused[shabad_id] = fused.get(shabad_id, 0.0) + 1 / (self.RRF_K + rank)
        ranked = sorted(fused, key=fused.get, reverse=True)

        results: list[SearchResult] = []
        for shabad_id in ranked:
            row = self._choose_line(shabad_id, query)
            if not self._passes_filters(row, request.filters):
                continue
            citation = row.get("citation") or {}
            if not citation.get("source_id") or not citation.get("ang"):
                continue
            has_lexical = shabad_id in lexical_scores
            has_semantic = shabad_id in semantic_scores
            if has_lexical and has_semantic:
                explanation = "Found by both keyword and semantic Shabad search."
            elif has_semantic:
                explanation = "Found by semantic similarity to the full Shabad."
            else:
                explanation = "Found by BM25 keyword relevance across the full Shabad."
            results.append(
                self._to_result(
                    row,
                    explanation,
                    lexical_scores.get(shabad_id),
                    semantic_scores.get(shabad_id),
                    fused[shabad_id],
                )
            )
            if len(results) >= request.top_k:
                break
        return results
