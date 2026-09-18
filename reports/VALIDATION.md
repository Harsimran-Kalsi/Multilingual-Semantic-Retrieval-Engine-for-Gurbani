# Validation report — 2026-09-18

## Outcome

The project now has a reproducible source-lookup evaluation, an ungraded
conceptual review workflow, offline correctness tests, and explicit search modes.
**Keyword search is the default for finding wording.** Hybrid search is an
optional exploration mode and powers Ask Gurbani when available.

## Corpus and live checks

- **43 offline tests passed** from an isolated staged Gurbani snapshot, without the uncommitted Gita experiment; network calls were disabled.
- The earlier working-tree run passed **50 tests**, including seven Gita tests. The original output is retained separately; these counts refer to different scopes.

- All **60,555** source records passed the JSON schema validator.
- **5,549** Shabads; persisted `text-embedding-3-small` vectors, **768** dimensions.
- Live embeddings succeeded for **120/120** known-item queries and **30/30**
  synthetic conceptual questions. No query fell back in these recorded runs.
- One end-to-end answer smoke test succeeded using the configured
  `gpt-5.6-terra` model, with five sources and valid citation IDs. This checks
  generation and reference validation, not semantic entailment or interpretive accuracy.
- Browser verification covered source search, full-passage navigation, and
  the offline review worksheet with complete context and blank ratings.

## Exact-source lookup benchmark

120 mechanically generated queries from 40 sampled Shabads, with 40 English,
40 corpus Roman-transliteration, and 40 Gurmukhi excerpts. The retrievers received
no language hints. This benchmark is source-derived silver data, **not** a
human-reviewed or independently held-out conceptual relevance evaluation.

| System | Queries with target in top 5 | Hit@5 | MRR@10 |
| --- | ---: | ---: | ---: |
| Combined-field BM25 | 112/120 | 93.3% | 0.868 |
| Multi-view keyword | 114/120 | 95.0% | 0.875 |
| Keyword + semantic (RRF) | 89/120 | 74.2% | 0.447 |

This result is why hybrid retrieval is optional for source search: its semantic
candidates displace exact targets on this task. No fusion weights were tuned to
these 120 questions. A conceptual relevance benefit has **not** been established.

The lexical improvement is two additional successful queries, with greater local
computation cost. The local latency samples are recorded in the JSON reports;
they exclude startup/index loading, HTTP, answer generation and concurrent load.
Hybrid first-pass times include external query-embedding latency, while warm
queries use the in-memory cache. These are not production latency claims.

The original 18-query fixture remains a small regression test. Quality figures
from either silver set must retain their task and sample-size qualifiers.

## Fixes verified

- Ang filters can find a matching line on a later page of a multi-page Shabad.
- Semantic candidates select lines satisfying the requested metadata filters.
- Embedding retrieval uses only the configured model's compatible finite vectors;
  invalid query vectors and provider errors fall back to keyword search.
- Citation validation rejects invalid or missing references for the entire answer
  instead of silently removing references while preserving associated claims.
- Whitespace-only and oversized queries, invalid filters, and oversized conversation
  context are rejected. Failed generation retains cited source results.
- Corpus validation now exits nonzero when records are invalid.
- Tests disable network/credentials and isolate local databases. The added GitHub
  Actions workflow is configured but has not been executed on GitHub in this task.

## Human review still required

The 30 assistant-authored conceptual/boundary questions have no relevance labels.
Their BM25, multi-view and hybrid candidates were pooled and shuffled into
**461 query/passage pairs**, with all grades blank. The offline worksheet includes
complete Gurmukhi source passages and attributed English translations. These are
not actual user questions or adoption evidence.

Open [relevance_review.html](relevance_review.html). Follow the
[data and review protocol](../data/eval/README.md), obtain knowledgeable reader
judgments, and keep an independently reviewed test split before future tuning.
Citation membership alone cannot validate the meaning of generated claims.

## Reproduction and artifacts

- [Committed Gurbani snapshot tests](committed_offline_tests.txt)
- [Earlier working-tree test output including Gita](offline_tests.txt)
- [Offline known-item results](known_item_lexical.json)
- [Live hybrid known-item results](known_item_hybrid.json)
- [Unjudged conceptual rankings](conceptual_unjudged_hybrid.json)
- [Blinded review pool](conceptual_review_pool.jsonl)
- [Live answer smoke result](live_answer_smoke.json)

JSON reports contain corpus/query/code/index fingerprints, model metadata,
per-language metrics, full rankings and fallback counts. They record the exact
implementation at measurement time; the subsequent default-mode selection and
embedding-build validation do not change the explicitly selected ranking modes
used in those experiments. The full final offline suite is recorded separately.

No trained embedding model, verified conceptual-accuracy gain, production scale,
real-user adoption, or public deployment is claimed.
