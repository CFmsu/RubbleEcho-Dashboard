"""Acoustic tools. `train` fits shape rules on synthetic 4-mic clips. `listen` opens the XVF3800."""

import argparse
import json
import sys

from app.audio.detector import detect_event
from app.drivers.respeaker import device_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RubbleEcho acoustic tools")
    commands = parser.add_subparsers(dest="command", required=True)
    extract = commands.add_parser("extract")
    extract.add_argument("--samples", default="")
    extract.add_argument("--rate", type=float, default=16000)
    for name in ("record", "label", "train", "evaluate", "listen", "report"):
        commands.add_parser(name)
    args = parser.parse_args(argv)
    if args.command == "extract":
        samples = _parse_samples(args.samples)
        print(json.dumps(detect_event(samples, args.rate)))
        return 0
    if args.command == "report":
        print(json.dumps(device_report()))
        return 0
    if args.command == "record":
        return _record()
    if args.command == "listen":
        return _listen()
    if args.command == "train":
        from app.audio.training import train_dummy

        print(json.dumps(train_dummy()))
        return 0
    if args.command == "evaluate":
        from app.audio.training import evaluate_dummy

        print(json.dumps(evaluate_dummy()))
        return 0
    print(json.dumps({
        "training_status": "SYNTHETIC_DUMMY",
        "hardware_calibrated": False,
        "message": "Labels are the synthetic generator's ground truth. There is no human session split and no piezo.",
    }))
    return 0


def _record() -> int:
    report = device_report()
    if report["state"] != "ready":
        print(json.dumps({
            "status": "UNAVAILABLE",
            "message": report["error"] or "No microphone was opened.",
            "report": report,
        }))
        return 2
    print(json.dumps({
        "status": "READY",
        "message": "Device is enumerated. Use `listen` to run the detector. This command does not write a WAV.",
        "report": report,
    }))
    return 0


def _listen() -> int:
    from app.audio.engine import start_listener, stop_listener

    started = start_listener()
    print(json.dumps(started))
    if not started["ok"]:
        return 2
    try:
        threading_wait()
    except KeyboardInterrupt:
        print(json.dumps(stop_listener()))
    return 0


def threading_wait() -> None:
    import time

    while True:
        time.sleep(0.5)


def _parse_samples(text: str) -> list[float]:
    if not text.strip():
        return []
    return [float(part) for part in text.split(",") if part.strip()]


if __name__ == "__main__":
    sys.exit(main())
