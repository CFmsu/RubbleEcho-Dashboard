"""Grab mmWave, microphone, and ultrasonic readings on the Pi.

Each function writes its file under ~/Desktop/sensor_drops/<time>/.
The same readings are posted to the laptop, which copies them into
backend/data/pi_inbox and asks the model to reason. The model does not
drive the rover.

Set MMWAVE_COMMAND and ULTRASONIC_COMMAND to the programs that write
mmwave.json and ultrasonic.json. The microphone command is already set.
"""

from __future__ import annotations

import json
import os
import shlex
import struct
import subprocess
import sys
import urllib.request
import wave
from datetime import datetime, timezone
from pathlib import Path

# Programs on the Pi that create JSON. Leave a line empty until that program exists.
MMWAVE_COMMAND = os.environ.get("MMWAVE_COMMAND", "")
ULTRASONIC_COMMAND = os.environ.get("ULTRASONIC_COMMAND", "")
MIC_DEVICE = os.environ.get("MIC_DEVICE", "plughw:0")
LISTEN_SECONDS = 7
LAPTOP = os.environ.get("LAPTOP", "http://172.20.10.2:5173")


def run_command(command: str, folder: Path) -> subprocess.CompletedProcess[str] | None:
    if not command.strip():
        print("ERROR : COMMAND IS EMPTY")
        return None
    try:
        result = subprocess.run(
            shlex.split(command),
            cwd=folder,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        print(f"ERROR : COMMAND FAILED TO RUN ({exc})")
        return None
    if result.returncode != 0:
        print("ERROR : COMMAND FAILED TO RUN")
        if result.stderr.strip():
            print(result.stderr.strip())
        return None
    return result


def _read_json(folder: Path, name: str, result: subprocess.CompletedProcess[str] | None) -> dict | None:
    path = folder / name
    if path.is_file():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else None
    if result is None:
        return None
    text = result.stdout.strip()
    if not text:
        return None
    loaded = json.loads(text)
    if not isinstance(loaded, dict):
        return None
    path.write_text(json.dumps(loaded, indent=2), encoding="utf-8")
    return loaded


def get_mmWave_data(folder: Path) -> dict | None:
    print("getting mmWave...")
    result = run_command(MMWAVE_COMMAND, folder)
    if result is None and not (folder / "mmwave.json").is_file():
        return None
    data = _read_json(folder, "mmwave.json", result)
    if not isinstance(data, dict):
        return None
    if "distance_cm" in data and "distance_m" not in data:
        data["distance_m"] = float(data["distance_cm"]) / 100.0
    (folder / "radar.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def get_microphone_data(folder: Path) -> dict | None:
    print("getting microphone...")
    wav_path = folder / "microphone.wav"
    command = f"arecord -f S16_LE -c 1 -r 16000 -d {LISTEN_SECONDS} -D {shlex.quote(MIC_DEVICE)} {shlex.quote(str(wav_path))}"
    if run_command(command, folder) is None:
        return None
    with wave.open(str(wav_path), "rb") as handle:
        rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
        width = handle.getsampwidth()
    if width != 2 or not frames:
        print("ERROR : microphone file is not 16-bit audio")
        return None
    count = len(frames) // 2
    samples = [sample / 32768.0 for sample in struct.unpack("<" + "h" * count, frames)]
    payload = {"sample_rate": rate, "samples": samples}
    (folder / "audio.json").write_text(
        json.dumps({"sample_rate": rate, "sample_count": len(samples)}),
        encoding="utf-8",
    )
    return payload


def get_ultrasonic_data(folder: Path) -> dict | None:
    print("getting ultrasonic...")
    result = run_command(ULTRASONIC_COMMAND, folder)
    if result is None and not (folder / "ultrasonic.json").is_file():
        return None
    data = _read_json(folder, "ultrasonic.json", result)
    if not isinstance(data, dict):
        return None
    if "distance_cm" not in data and "distance" in data:
        data = {"distance_cm": float(data["distance"])}
    if data.get("distance_cm") is None:
        print("ERROR : ultrasonic JSON has no distance_cm")
        return None
    (folder / "ultrasonic.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"distance_cm": float(data["distance_cm"])}


def send_to_laptop(folder: Path, radar: dict | None, audio: dict | None, ultrasonic: dict | None) -> None:
    payload: dict = {"reason": True}
    if radar:
        payload["radar"] = radar
    if audio:
        payload["audio"] = {"sample_rate": audio["sample_rate"], "samples": audio["samples"]}
    if ultrasonic:
        payload["ultrasonic"] = ultrasonic
    if len(payload) == 1:
        print("Nothing was captured, so nothing was sent.")
        return
    url = LAPTOP.rstrip("/") + "/api/pi/ingest"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.loads(response.read().decode("utf-8"))
    print("Laptop stored the files at", body.get("folder"))
    reasoning = body.get("reasoning") if isinstance(body.get("reasoning"), dict) else {}
    text = reasoning.get("narrative") or reasoning.get("summary")
    print(text or "The model did not return a briefing.")
    (folder / "laptop.json").write_text(json.dumps(body.get("reasoning"), indent=2), encoding="utf-8")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = Path.home() / "Desktop" / "sensor_drops" / stamp
    folder.mkdir(parents=True, exist_ok=True)
    print("Saving on the Pi at", folder)
    radar = get_mmWave_data(folder)
    audio = get_microphone_data(folder)
    ultrasonic = get_ultrasonic_data(folder)
    send_to_laptop(folder, radar, audio, ultrasonic)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        LAPTOP = sys.argv[1]
    main()
