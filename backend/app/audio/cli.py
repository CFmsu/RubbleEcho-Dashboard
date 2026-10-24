"""Audio workflow commands. They do not train on synthetic clips."""

import argparse
import json
import sys

from app.audio.detector import detect_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RubbleEcho acoustic tools")
    commands = parser.add_subparsers(dest="command", required=True)
    extract = commands.add_parser("extract")
    extract.add_argument("--samples", default="")
    extract.add_argument("--rate", type=float, default=16000)
    for name in ("record", "label", "train", "evaluate"):
        commands.add_parser(name)
    args = parser.parse_args(argv)
    if args.command == "extract":
        samples = _parse_samples(args.samples)
        print(json.dumps(detect_event(samples, args.rate)))
        return 0
    if args.command == "record":
        print(json.dumps({
            "status": "UNAVAILABLE",
            "message": "No microphone was opened. Run arecord -l on the Pi before recording.",
        }))
        return 2
    print(json.dumps({
        "training_status": "NOT_TRAINED",
        "message": "No genuine labeled session split is available.",
    }))
    return 0


def _parse_samples(text: str) -> list[float]:
    if not text.strip():
        return []
    return [float(part) for part in text.split(",") if part.strip()]


if __name__ == "__main__":
    sys.exit(main())
