# Multilingual Semantic Retrieval Engine for Gurbani

Search the Sri Guru Granth Sahib with citations using Gurmukhi, common Roman
Punjabi terms, or a practical set of English concepts.

## Current State

- FastAPI backend with `/search` and `/health`
- Web UI at `/`
- Clickable result cards with animated full-Shabad reading context
- Corpus-backed retrieval across 60,555 SGGS lines
- Unicode Gurmukhi, Roman transliteration, English translation, Ang, writer,
  section/Raag, and stable Shabad OS line IDs
- Lightweight alias + lexical/character retrieval (no API key or vector database)

## Run App

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/` (UI)
- `http://127.0.0.1:8000/docs` (API docs)

Try searches such as `simran`, `inner peace`, `naam`, `hukam`, `ਸਿਮਰਨ`, or
`ਹੁਕਮ`.

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

## Validation

Validate runtime corpus:

```bash
.venv/bin/python scripts/prepare_corpus.py --input data/sggs.jsonl
.venv/bin/python -m unittest discover -s tests
```
