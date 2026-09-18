# Retrieval evaluation data

These files serve different purposes. Do not merge their labels or report one
undifferentiated accuracy figure.

| File | Contents | Valid interpretation |
| --- | --- | --- |
| `sggs_retrieval_silver.jsonl` | Original 18 direct-correspondence queries | Small regression fixture |
| `sggs_known_item_v1.jsonl` | 120 queries, 40 sampled passages, 40 each in English, Gurmukhi, and corpus Roman transliteration | Mechanically labelled known-item/source lookup |
| `sggs_conceptual_review_v1.jsonl` | 30 assistant-authored conceptual and boundary-case questions | Unjudged review candidates; not real user queries |

## Reproduce the known-item set

Run `python scripts/build_known_item_eval.py` from the repository root. The
fixed seed is 20260918. Sampling selects one eligible Shabad from each of 40
strata across canonical corpus order, then extracts eight consecutive words
from a line in each of its three representations. Every passage containing
that exact whitespace-normalized excerpt is included in the target set.
Each row records the corpus SHA-256, source line, field, method, and seed.

The corpus transliteration is not equivalent to arbitrary informal Roman
Punjabi spelling. These are easy source-derived lookup queries. They are not
independent human judgments, paraphrase tests, theological interpretation
tests, or a held-out conceptual relevance benchmark. Repeated or related
passages may remain relevant beyond the mechanically defined exact targets.

## Human review procedure

1. Open `reports/relevance_review.html` in a browser. It works offline and
   contains complete passages; candidate order is shuffled and system labels
   are hidden. All grades begin blank. Do not treat blank grades as zero.
2. Have a knowledgeable reader check the questions (especially Roman Punjabi)
   and grade complete passages: 0 irrelevant, 1 topically related, 2 partly
   answers, 3 directly useful. Record an alias and export ratings. A second
   independent reader should review a subset and resolve disagreements.
3. Treat claims about guaranteed outcomes, out-of-domain questions and prompt
   injection separately. An all-zero pool may mean an unanswerable question
   or missing retrieval candidates, not proof that the corpus has no answer.
4. Before tuning on reviewed labels, freeze separate development and test
   question groups, keeping near-duplicates and the same underlying intent
   together. Collect new independent questions for final evaluation. The
   current assistant-authored pack is not such a held-out test.
5. Convert complete reviewed rows into evaluator JSONL containing `id`,
   `query`, `language`, `relevant_shabad_ids`, optional positive integer
   `relevance_grades` (1 to 3), and reviewer/provenance metadata. Evaluate
   all-zero or partially reviewed questions separately; do not drop them
   silently from an overall success claim.

Pooled labels are incomplete judgments of the full corpus. Systems that
contribute candidates can have an evaluation advantage over future systems;
expand the pool and review new candidates when comparing a new retriever.

## Metric definitions

- Hit@k: fraction of judged queries with at least one target in the first k.
- Recall@k: fraction of each query's labelled target passages retrieved,
  macro-averaged over judged queries.
- MRR@10: reciprocal rank of the first target, zero when absent.
- nDCG@k: discounted graded relevance relative to the ideal labelled ranking;
  binary relevance is used when no grades are supplied.

Unjudged conceptual questions produce rankings and a review pool only, never
quality metrics. Latency measurements exclude index initialization, HTTP and
answer generation. First-pass hybrid times include query embedding requests;
successful repeated queries reuse the in-memory embedding cache. They are
local sequential measurements, not production latency or load-test results.
