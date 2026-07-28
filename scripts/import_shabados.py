#!/usr/bin/env python3
"""Export Sri Guru Granth Sahib Ji from a pinned Shabad OS SQLite release."""

import argparse
import json
import re
import sqlite3
from pathlib import Path


# Ported from Shabad OS gurmukhi-utils 3.2.2 (MIT).
# Multi-character mappings must remain before single-character mappings.
UNICODE_MAPPINGS = {
    "ei": "ਇ", "au": "ਉ", "aU": "ਊ", "eI": "ਈ", "ey": "ਏ", "Aw": "ਆ",
    "AY": "ਐ", "AO": "ਔ", "AW": "ਆਂ", "<>": "ੴ", "ÅÆ": "ੴ", "ƒ": "ਨੂੰ",
    "†": "੍ਟ", "˜": "੍ਨ", "Î": "੍ਯ", "î": "੍ਯ", "ç": "੍ਚ", "œ": "੍ਤ",
    "M": "ੰ", "H": "੍ਹ", "§": "੍ਹੂ", "i": "ਿ", "I": "ੀ", "u": "ੁ", "U": "ੂ",
    "y": "ੇ", "Y": "ੈ", "N": "ਂ", "o": "ੋ", "O": "ੌ", "R": "੍ਰ", "W": "ਾਂ",
    "w": "ਾ", "®": "੍ਰ", "´": "ੵ", "Ï": "ੵ", "µ": "ੰ", "μ": "ੰ", "@": "ੑ",
    "`": "ੱ", "~": "ੱ", "Í": "੍ਵ", "Ú": "ਃ", "ü": "ੁ", "|": "ਙ", "¨": "ੂ",
    "Ø": "", "ˆ": "ਂ", "¤": "ੱ", "a": "ੳ", "A": "ਅ", "b": "ਬ", "B": "ਭ",
    "c": "ਚ", "C": "ਛ", "d": "ਦ", "D": "ਧ", "e": "ੲ", "E": "ਓ", "f": "ਡ",
    "F": "ਢ", "g": "ਗ", "G": "ਘ", "h": "ਹ", "j": "ਜ", "J": "ਝ", "k": "ਕ",
    "K": "ਖ", "l": "ਲ", "L": "ਲ਼", "m": "ਮ", "n": "ਨ", "p": "ਪ", "P": "ਫ",
    "q": "ਤ", "Q": "ਥ", "r": "ਰ", "s": "ਸ", "S": "ਸ਼", "t": "ਟ", "T": "ਠ",
    "v": "ਵ", "V": "ੜ", "x": "ਣ", "X": "ਯ", "z": "ਜ਼", "Z": "ਗ਼", "1": "੧",
    "2": "੨", "3": "੩", "4": "੪", "5": "੫", "6": "੬", "^": "ਖ਼", "7": "੭",
    "&": "ਫ਼", "8": "੮", "9": "੯", "0": "੦", "[": "।", "]": "॥", "Ò": "॥",
    "\\": "ਞ", "ï": "ਯ", "Ç": "☬", "¡": "ੴ", "æ": "਼", "‚": "❁",
}


def to_unicode(text: str) -> str:
    text = re.sub(r"i(.)", r"\1i", text)
    text = text.replace("®", "R")
    text = re.sub(r"([iMµyY])([RH§ÍÏçœ˜†])", r"\2\1", text)
    text = re.sub(r"([MµyY])([uU])", r"\2\1", text)
    text = re.sub(r"`([wWIoOyYRH§´ÍÏçœ˜†uU])", r"\1`", text)
    text = re.sub(r"i([´Î])", r"\1i", text)
    text = text.replace("uo", "ou")
    for source, target in UNICODE_MAPPINGS.items():
        text = text.replace(source, target)
    return text


QUERY = """
SELECT
    l.id,
    l.source_page,
    l.source_line,
    l.gurmukhi,
    tr.transliteration,
    tx.translation,
    ts.name_english AS translator,
    w.name_english AS author,
    sec.name_english AS section
FROM lines l
JOIN shabads sh ON sh.id = l.shabad_id
JOIN writers w ON w.id = sh.writer_id
JOIN sections sec ON sec.id = sh.section_id
LEFT JOIN transliterations tr
    ON tr.line_id = l.id AND tr.language_id = 1
LEFT JOIN translations tx
    ON tx.line_id = l.id AND tx.translation_source_id = 1
LEFT JOIN translation_sources ts
    ON ts.id = tx.translation_source_id
WHERE sh.source_id = 1
ORDER BY l.order_id
"""


def export(database: Path, output: Path, release: str) -> int:
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as target:
        for row in connection.execute(QUERY):
            translations = []
            if row["translation"]:
                translations.append(
                    {
                        "lang": "en",
                        "text": row["translation"],
                        "translator": row["translator"],
                    }
                )
            record = {
                "verse_id": f"shabados:{row['id']}",
                "gurmukhi": to_unicode(row["gurmukhi"]),
                "transliteration": row["transliteration"],
                "translation": row["translation"],
                "translations": translations,
                "citation": {
                    "source_id": f"shabados:{release}:line:{row['id']}",
                    "ang": row["source_page"],
                    "raag": row["section"],
                    "author": row["author"],
                    "line_start": row["source_line"],
                    "line_end": row["source_line"],
                },
            }
            target.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    connection.close()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output", default="data/sggs.jsonl", type=Path)
    parser.add_argument("--release", required=True)
    args = parser.parse_args()
    count = export(args.database, args.output, args.release)
    print(f"Wrote {count} SGGS lines to {args.output}")


if __name__ == "__main__":
    main()
