#!/usr/bin/env python3
"""Build the persistent Shabad search index and optional semantic embeddings."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from backend.app.retrieval import CorpusRetriever


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--embeddings",
        action="store_true",
        help="Generate missing OpenAI embeddings (requires OPENAI_API_KEY).",
    )
    parser.add_argument("--dimensions", type=int, default=768)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    retriever = CorpusRetriever()
    print(
        f"Indexed {len(retriever.records):,} lines in "
        f"{len(retriever.shabads):,} Shabads at {retriever.index_path}"
    )
    if args.embeddings:
        added = retriever.build_embeddings(
            dimensions=args.dimensions,
            batch_size=args.batch_size,
        )
        print(f"Added {added:,} semantic embeddings.")


if __name__ == "__main__":
    main()
