# TRACE — Multilingual Search Engine

**TRACE stands for Text Retrieval And Context Exploration.**

TRACE is a search and reading application for the **Sri Guru Granth Sahib**, a
corpus of Sikh scripture. It searches **60,555 source lines across 5,549 Shabads**
(passages), accepts English, Gurmukhi, and Roman Punjabi queries, and connects
ranked results to their original wording and complete passage context.

A reader may remember a translated idea, a Punjabi word written in Latin
characters, or part of an original line. TRACE brings those entry points into
one interface: search, inspect the source, and open the surrounding passage.
Optional AI explanations include citations that link back to retrieved records.

The name reflects the app's workflow: retrieve text, then explore its context.
The source text and translation are attributed in the [dataset section](#dataset).

[Run locally](#run-app) · [Architecture](#retrieval-and-grounding) ·
[Evaluation](#evaluation-at-a-glance) · [Source attribution](#dataset)

## How to Use It

1. **Find wording:** search for source text with the default keyword mode.
2. **Inspect the result:** compare the Gurmukhi, transliteration, and English
   translation alongside its Ang (page), author, Raag, and stable source ID.
3. **Read in context:** open the complete Shabad from a result.
4. **Explore further:** opt into hybrid retrieval or request an AI explanation.
   Citation-ID checks verify source membership; interpretation still needs review.

The interface currently labels the optional modes **Explore meaning** and
**Ask Gurbani**. Source search and passage reading work locally without an API key.

## What It Does

- Searches 60,555 source lines across 5,549 Shabads with keyword lookup and optional hybrid retrieval.
- Supports English concepts, common Roman Punjabi vocabulary, and Gurmukhi.
- Shows Gurmukhi, transliteration, English translation, Ang, author, Raag, and
  stable source IDs.
- Opens any result into its complete Shabad context.
- Collects anonymous Helpful / Not relevant ratings on individual results.
- Can generate an optional plain-language overview, instructed to use the selected
  retrieved source lines as evidence.
- Rejects generated answers containing missing or invalid citation IDs before returning them.
- Supports grounded follow-up questions without treating earlier AI prose as
  scriptural evidence.

## Retrieval and Grounding

```text
Browser interface → FastAPI
                       │
             Retrieval mode selection
              ├── Keyword: SQLite FTS5 / BM25 (default)
              └── Hybrid: keyword + embedding search → rank fusion
                       │
              Ranked source lines + stable IDs
              ├── Source cards → complete-passage reader
              └── Optional AI answer → citation-ID validation
```

The full-text and semantic searches operate at Shabad level so a line can be
found through its surrounding meaning. The UI and generated answer cite ranked
source lines. Complete passages are available in the reader; generation receives
selected lines rather than every line in those passages.
Embeddings are stored in the local SQLite index;
no hosted vector database is required.

Lexical retrieval uses a combined Shabad-level BM25 baseline plus independently
weighted English translation, Roman Punjabi transliteration, Gurmukhi, and
exact-line views. The combined baseline remains dominant; script-aware views
provide lower-weight ranking signals. The API reports `keyword` or `hybrid`
retrieval explicitly. Its `fusion_score` is the Reciprocal Rank Fusion value,
not a learned reranker score.

**Find wording** is the default source-search mode. **Explore meaning** opts
into hybrid retrieval; **Ask Gurbani** also uses hybrid retrieval when available.
The 120-query source-lookup evaluation found that adding semantic retrieval
reduced exact-source hit rate, so hybrid is an explicit choice rather than an
automatic upgrade whenever credentials are present. See the
[validation report](reports/VALIDATION.md) for the complete comparison and limitations.

### Technology

| Layer | Implementation |
| --- | --- |
| Browser interface | HTML, CSS, and JavaScript for search, passage reading, and feedback |
| API and validation | Python, FastAPI, Pydantic, and JSON Schema |
| Keyword index | SQLite FTS5 with BM25 and separate language views |
| Semantic retrieval | Shabad embeddings, local NumPy cosine scoring, and reciprocal rank fusion |
| Optional generation | Configurable OpenAI model with structured answers and citation-ID checks |
| Evaluation and checks | Reproducible query fixtures, isolated offline tests, and a GitHub Actions workflow |

### Engineering Decisions

- **Keep sources inspectable.** Each line carries the pinned corpus release and
  source ID; readers can move from a result to its complete passage.
- **Select defaults using measurements.** Keyword search performed better on the
  current exact-source lookup benchmark, so hybrid search is an explicit option.
- **Keep retrieval available during provider failures.** Missing embeddings or
  embedding-provider failures fall back to keyword search. Failed answer
  generation preserves the retrieved source results.
- **Separate reference checks from interpretation.** Missing or invalid citation
  IDs cause an answer to be rejected. Valid IDs alone do not establish that a
  generated claim follows from its cited text.

## Evaluation at a Glance

The reproducible lookup benchmark contains **120 source-derived queries** from
40 sampled passages: 40 English excerpts, 40 corpus Roman-transliteration
excerpts, and 40 Gurmukhi excerpts.

| Retrieval method | Queries with target passage in top 5 |
| --- | ---: |
| Combined-field BM25 | 112 / 120 |
| Multi-view keyword search | 114 / 120 |
| Keyword + semantic retrieval (RRF) | 89 / 120 |

These results measure known-source lookup on this fixture. They do not measure
general answer accuracy, conceptual relevance, or success with independently
supplied user questions. The committed validation report also records **43
passing offline tests** for its isolated Gurbani snapshot.

See the [validation report](reports/VALIDATION.md) for methodology, recorded
results, and limitations, and [Validation and Tests](#validation-and-tests) to
reproduce the checks. The [comparison pilot](#product-comparison-pilot) records
additional phrase-lookup failures that remain useful development cases.

## Run App

```bash
git clone https://github.com/Harsimran-Kalsi/Multilingual-Semantic-Retrieval-Engine-for-Gurbani.git
cd Multilingual-Semantic-Retrieval-Engine-for-Gurbani
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Interactive API
documentation is available at
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Source search works locally without an API key. To enable grounded answers and
semantic retrieval, copy `.env.example` to `.env` and add your key:

```bash
cp .env.example .env
```

```dotenv
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-5.6-terra
```

The ignored `.env` file and generated SQLite index are never committed.

Keyword lookup and passage reading run locally. Optional query embeddings send
the query text to the configured provider; building embeddings sends corpus text.
Answer generation sends the question, selected source lines, and supplied
conversation context. API keys belong in the ignored `.env` file, not in browser
code or committed configuration.

The local BM25 index is created automatically as `data/search.sqlite`. To add
semantic retrieval, generate the embeddings once:

```bash
.venv/bin/python scripts/build_search_index.py --embeddings
```

Later app starts reuse those embeddings. If no key or embeddings are available,
the indexed BM25 search remains fully functional.

Restart the Uvicorn server after configuring `.env` or building embeddings so
the application reloads its configuration and embedding index.

## Questions to Try

- `How can I overcome my ego in everyday life?`
- `What does Gurbani teach about serving others?`
- `How should I deal with fear of death?`
- `What does it mean to live according to Hukam?`
- `How can I find peace when my mind is restless?`
- `Why should we remember Naam?`
- `ਕੀ ਹੁਕਮ ਹੈ?`
- `ਸਿਮਰਨ`

After an answer, try a follow-up such as `What practical actions do these
passages recommend?`

## Dataset

The app reads one generated runtime file:

- `data/sggs.jsonl` (or set `CORPUS_PATH`)

It was generated from the official
[Shabad OS Database](https://github.com/shabados/database) SQLite release
`4.8.7`. Each citation contains that release and the stable Shabad OS line ID.
English translations in this export are attributed to Dr. Sant Singh Khalsa.
See the Shabad OS [database sources](https://www.shabados.com/docs/database/sources/)
and [license](https://github.com/shabados/database/blob/main/LICENSE.md).

To regenerate it from the pinned release:

```bash
curl -L https://github.com/shabados/database/releases/download/4.8.7/database.sqlite \
  -o /tmp/shabados-database-4.8.7.sqlite
.venv/bin/python scripts/import_shabados.py \
  --database /tmp/shabados-database-4.8.7.sqlite \
  --release 4.8.7 \
  --output data/sggs.jsonl
```

Runtime schema: `data/schema/verse.schema.json`.

## API

- `POST /search` retrieves cited SGGS lines; `mode` is `lexical` (default) or `hybrid`.
- `POST /ask` retrieves sources and produces a grounded answer.
- `GET /passage/{verse_id}` returns the complete Shabad for a selected line.
- `GET /reader/{verse_id}` returns a reading window around a source line.
- `GET /health` reports server health.
- `POST /feedback` records a validated local relevance rating.

## Relevance Feedback

Each result card has **Helpful** and **Not relevant** controls. Ratings are
stored locally in the ignored `data/feedback.sqlite` file together with the
query, result position, stable source ID, and retrieval scores. No user identity
is collected.

After collecting ratings, print a compact relevance report:

```bash
.venv/bin/python scripts/summarize_feedback.py
```

The report shows the overall helpful rate, performance by result position, and
queries with the weakest feedback. This creates a small evidence loop for
improving retrieval rather than tuning it only by intuition.

## Validation and Tests

Install test dependencies, validate the corpus, and run the isolated offline suite:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/prepare_corpus.py --input data/sggs.jsonl
.venv/bin/python scripts/run_offline_tests.py
```

The runner disables credentials and network connections and uses temporary
index/feedback databases. Tests include actual dense cosine ranking and fusion
with a fake embedding provider, provider failures, model/index compatibility,
multi-page Ang filtering, citation rejection, request validation, and API flows.
The GitHub Actions workflow runs this offline suite without API secrets.

Reproduce the larger source-lookup benchmark and run the offline comparison:

```bash
.venv/bin/python scripts/build_known_item_eval.py
.venv/bin/python scripts/evaluate_retrieval.py --output reports/known_item_lexical.json
```

Hybrid evaluation is explicit and makes live query-embedding requests using
the project's configured key. It reuses existing corpus embeddings and does
not regenerate them. Both modes evaluate temporary copies of the index:

```bash
.venv/bin/python scripts/evaluate_retrieval.py --mode hybrid --repeats 1 --output reports/known_item_hybrid.json
.venv/bin/python scripts/evaluate_retrieval.py --judgments data/eval/sggs_conceptual_review_v1.jsonl --mode hybrid --repeats 1 --output reports/conceptual_unjudged_hybrid.json --review-output reports/conceptual_review_pool.jsonl
.venv/bin/python scripts/export_relevance_review.py
```

Reports include input/code/index fingerprints, model and corpus metadata,
per-language metrics, complete rankings, local latency samples and semantic
fallback counts. A hybrid run exits nonzero if any query falls back. The
30 conceptual questions have **no relevance labels** and therefore produce
no quality score. Open `reports/relevance_review.html` for an offline worksheet
with complete source passages and exportable human ratings. See the
[data and review protocol](data/eval/README.md) before interpreting results.

## Current limitations

- The 120 source-derived queries measure known-item lookup; conceptual
  relevance and improved semantic quality have not been established by human review.
- Citation-ID validation proves that references belong to retrieved sources,
  not that each generated claim is entailed by the cited passage.
- The longest Shabads are truncated to first/last context when embedded.
  The complete text remains available to keyword search and passage reading.
- Dense ranking is an exact NumPy matrix scan over the local corpus, not an
  approximate-nearest-neighbor service or a custom-trained embedding model.
- Prior questions provide generation context; retrieval uses the current
  question, so ambiguous follow-ups may need their topic restated.
- No public deployment, production load test, or real-user adoption is claimed.

## Repository Guide

| Path | Contents |
| --- | --- |
| [`backend/app/`](backend/app/) | API routes, retrieval, generation, schemas, and feedback storage |
| [`frontend/index.html`](frontend/index.html) | Browser search and reading interface |
| [`data/`](data/) | Pinned corpus export, schema, and evaluation fixtures |
| [`scripts/`](scripts/) | Corpus import, index building, evaluation, and review tools |
| [`tests/`](tests/) | Offline retrieval, validation, and API checks |
| [`reports/VALIDATION.md`](reports/VALIDATION.md) | Recorded measurements and their limitations |
| [`.github/workflows/tests.yml`](.github/workflows/tests.yml) | Automated offline test workflow |

## Scope

This is a research and reading aid, not an authority on Sikhi or a replacement
for studying Gurbani with knowledgeable teachers and the wider tradition.
Generated explanations are instructed to use the selected retrieved source lines
and included English translation, currently attributed to Dr. Sant Singh Khalsa. Exact
Gurmukhi source lines are always presented so interpretations can be checked.

## Product comparison pilot

A three-question comparison with user-supplied ChatGPT file-upload answers exposed
phrase lookup and context-retrieval weaknesses. ChatGPT provided more direct evidence
on these examples, with one incorrect Shabad ID. This is a synthetic development
pilot, not an independently graded product benchmark. See the
[comparison findings](reports/product_validation/COMPARISON.md) and
[pilot protocol](reports/product_validation/README.md).
