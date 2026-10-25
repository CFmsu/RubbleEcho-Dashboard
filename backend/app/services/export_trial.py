import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone

from app.config.geometry import load_geometry
from app.version import APP_VERSION


def build_export(trial: dict, git_sha: str, attachments: dict[str, bytes] | None = None) -> bytes:
    events = trial.get("events", [])
    samples = trial.get("samples", [])
    reasoning = trial.get("reasoning")
    geometry = load_geometry()
    events_blob = "".join(json.dumps(event) + "\n" for event in events).encode("utf-8")
    measurements = _measurements_csv(samples)
    if reasoning is None:
        inference_blob = b""
        inference_count = 0
    else:
        inference_blob = (json.dumps(reasoning) + "\n").encode("utf-8")
        inference_count = 1
    readme = (
        "RubbleEcho trial export\n"
        f"trial_id: {trial['trial_id']}\n"
        f"source_mode: {trial.get('mode')}\n"
        "Units: geometry cm, ultrasonic cm, audio dBFS (not dB SPL), piezo adc_counts.\n"
        "actual_source is operator-entered. Mission telemetry does not use it for scoring.\n"
        "This archive contains no API keys.\n"
        "Heuristic scores are uncalibrated.\n"
    ).encode("utf-8")
    files = {
        "events.jsonl": events_blob,
        "measurements.csv": measurements,
        "inference.jsonl": inference_blob,
        "README.txt": readme,
    }
    for name, blob in (attachments or {}).items():
        if name.startswith("/") or ".." in name or "\\" in name:
            raise ValueError("unsafe archive path")
        files[name] = blob
    manifest = {
        "trial_id": trial["trial_id"],
        "app_version": APP_VERSION,
        "git_sha": git_sha,
        "exported_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "created_utc": trial.get("created_utc"),
        "source_mode": trial.get("mode"),
        "geometry_revision": geometry["geometry_revision"],
        "drawing_revision": geometry["drawing"]["revision"],
        "actual_source": trial.get("actual_source", "not_recorded"),
        "sand_depth": trial.get("sand_depth"),
        "cover_depth_cm": trial.get("cover_depth_cm"),
        "model_identity": None if not reasoning else reasoning.get("model_id"),
        "provider": None if not reasoning else reasoning.get("provider"),
        "event_count": len(events),
        "sample_count": len(samples),
        "inference_count": inference_count,
        "checksums": {name: hashlib.sha256(blob).hexdigest() for name, blob in files.items()},
        "units": {
            "geometry": "cm",
            "ultrasonic": "cm",
            "audio_level": "dBFS",
            "piezo": "adc_counts",
        },
        "limitations": trial.get("limitations", []),
        "calibration_id": trial.get("calibration_id"),
    }
    if "NEBIUS_API_KEY" in json.dumps(manifest) or "OPERATOR_TOKEN" in json.dumps(manifest):
        raise RuntimeError("export tried to include a secret field")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _write(archive, "manifest.json", json.dumps(manifest, indent=2).encode("utf-8"))
        for name, blob in files.items():
            _write(archive, name, blob)
    return buffer.getvalue()


def _measurements_csv(samples: list[dict]) -> bytes:
    fieldnames = [
        "captured_at_utc",
        "sensor",
        "quantity",
        "value",
        "unit",
        "quality",
        "mode",
        "x_cm",
        "y_cm",
    ]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for sample in samples:
        writer.writerow({key: sample.get(key) for key in fieldnames})
    return stream.getvalue().encode("utf-8")


def _write(archive: zipfile.ZipFile, name: str, blob: bytes) -> None:
    if name.startswith("/") or ".." in name or "\\" in name:
        raise ValueError("unsafe archive path")
    archive.writestr(name, blob)
