#!/usr/bin/env python3
"""Print a compact report of locally collected search relevance feedback."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.feedback import FeedbackStore


def main() -> None:
    summary = FeedbackStore().summary()
    print(
        f"Ratings: {summary['total']} | Helpful: {summary['helpful']} "
        f"({summary['helpful_percent']:.1f}%)"
    )
    print("\nHelpful rate by result position:")
    if not summary["by_rank"]:
        print("  No feedback recorded yet.")
    for row in summary["by_rank"]:
        percent = 100 * row["helpful"] / row["total"]
        print(f"  #{row['result_rank']}: {row['helpful']}/{row['total']} ({percent:.1f}%)")
    print("\nQueries needing attention:")
    if not summary["weak_queries"]:
        print("  No feedback recorded yet.")
    for row in summary["weak_queries"]:
        print(
            f"  {row['helpful_percent']:5.1f}% helpful across "
            f"{row['ratings']} rating(s): {row['query']}"
        )


if __name__ == "__main__":
    main()
