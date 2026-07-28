#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from jsonschema import validate


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_records(input_path: Path, schema_path: Path) -> tuple[int, int]:
    schema = load_json(schema_path)
    total = 0
    invalid = 0

    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                record = json.loads(line)
                validate(instance=record, schema=schema)
            except Exception:
                invalid += 1

    return total, invalid


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Gurbani JSONL corpus against verse schema.")
    parser.add_argument("--input", required=True, help="Path to JSONL corpus file")
    parser.add_argument("--schema", default="data/schema/verse.schema.json", help="Schema path")
    args = parser.parse_args()

    total, invalid = validate_records(Path(args.input), Path(args.schema))
    valid = total - invalid
    print(f"Total records: {total}")
    print(f"Valid records: {valid}")
    print(f"Invalid records: {invalid}")


if __name__ == "__main__":
    main()
