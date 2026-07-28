# Multilingual Semantic Retrieval Engine for Gurbani

Explore the Sri Guru Granth Sahib through multilingual source search and
citation-grounded answers. Ask conceptual questions in English, search common
Roman Punjabi terms, or enter Gurmukhi—and always trace the result back to its
exact Ang and Shabad OS source line.

## What It Does

- Searches 5,549 complete Shabads with hybrid lexical and semantic retrieval.
- Supports English concepts, common Roman Punjabi vocabulary, and Gurmukhi.
- Shows Gurmukhi, transliteration, English translation, Ang, author, Raag, and
  stable source IDs.
- Opens any result into its complete Shabad context.
- Generates an optional plain-language overview using only retrieved passages.
- Validates generated citation IDs before returning an answer.
- Supports grounded follow-up questions without treating earlier AI prose as
  scriptural evidence.

## Retrieval and Grounding

```text
Question
   ├── SQLite FTS5 / BM25 keyword search
   └── Shabad-level semantic embedding search
                  ↓
       Reciprocal Rank Fusion (RRF)
                  ↓
       Diverse, exact line citations
                  ↓
       Citation-constrained AI answer
```

The full-text and semantic searches operate at Shabad level so a line can be
found through its surrounding meaning. The UI and generated answer still cite
the most relevant exact line. Embeddings are stored in the local SQLite index;
no hosted vector database is required.

## Run App

```bash
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

The local BM25 index is created automatically as `data/search.sqlite`. To add
semantic retrieval, generate the embeddings once:

```bash
.venv/bin/python scripts/build_search_index.py --embeddings
```

Later app starts reuse those embeddings. If no key or embeddings are available,
the indexed BM25 search remains fully functional.

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

- `POST /search` retrieves cited SGGS lines.
- `POST /ask` retrieves sources and produces a grounded answer.
- `GET /passage/{verse_id}` returns the complete Shabad for a selected line.
- `GET /health` reports server health.

## Validation and Tests

Validate the corpus and run the test suite:

```bash
.venv/bin/python scripts/prepare_corpus.py --input data/sggs.jsonl
.venv/bin/python -m unittest discover -s tests
```

## Scope

This is a research and reading aid, not an authority on Sikhi or a replacement
for studying Gurbani with knowledgeable teachers and the wider tradition.
Generated explanations are limited to the retrieved passages and the included
English translation, currently attributed to Dr. Sant Singh Khalsa. Exact
Gurmukhi source lines are always presented so interpretations can be checked.
