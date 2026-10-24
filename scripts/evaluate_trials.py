"""Compute event metrics when a human supplies labels. The sample fixture is not a field result."""

import argparse
import json


def score_events(pairs: list[tuple[str, str]]) -> dict:
    labels = sorted({truth for _, truth in pairs} | {pred for pred, _ in pairs})
    counts = {label: {"tp": 0, "fp": 0, "fn": 0} for label in labels}
    for predicted, truth in pairs:
        if predicted == truth:
            counts[truth]["tp"] += 1
        else:
            counts[predicted]["fp"] += 1
            counts[truth]["fn"] += 1
    report = {}
    for label, row in counts.items():
        precision = row["tp"] / (row["tp"] + row["fp"]) if row["tp"] + row["fp"] else None
        recall = row["tp"] / (row["tp"] + row["fn"]) if row["tp"] + row["fn"] else None
        report[label] = {"precision": precision, "recall": recall, **row}
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", help="JSON list of [predicted, truth] pairs")
    args = parser.parse_args()
    if not args.pairs:
        print("labeled hardware metrics: not measured")
        print("Pass --pairs with a JSON list after a real labeled trial.")
        return 0
    pairs = [tuple(item) for item in json.loads(args.pairs)]
    print(json.dumps(score_events(pairs), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
