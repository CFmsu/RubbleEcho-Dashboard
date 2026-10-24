import io
import json
import zipfile

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_export_archive_is_complete_and_secret_free(auth_header) -> None:
    started = client.post(
        "/api/trials/start",
        json={"mode": "replay", "fixture": "../secrets"},
        headers=auth_header,
    )
    assert started.status_code == 404

    started = client.post(
        "/api/trials/start",
        json={"mode": "live"},
        headers=auth_header,
    )
    assert started.status_code == 409
    assert started.json()["detail"]["code"] == "NEEDS_HARDWARE_VERIFICATION"

    started = client.post(
        "/api/trials/start",
        json={"mode": "replay", "fixture": "sample_trial"},
        headers=auth_header,
    )
    trial_id = started.json()["trial_id"]
    denied = client.get(f"/api/trials/{trial_id}/export")
    assert denied.status_code == 401

    response = client.get(f"/api/trials/{trial_id}/export?format=zip", headers=auth_header)
    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = archive.namelist()
    assert names == [
        "manifest.json",
        "events.jsonl",
        "measurements.csv",
        "inference.jsonl",
        "README.txt",
    ]
    assert all(not name.startswith("/") and ".." not in name for name in names)
    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    events = archive.read("events.jsonl").decode("utf-8").strip().splitlines()
    assert manifest["event_count"] == len(events)
    assert manifest["source_mode"] == "replay"
    assert manifest["actual_source"] == "not_recorded"
    assert manifest["units"]["ultrasonic"] == "cm"
    blob = response.content.decode("latin1")
    assert "NEBIUS_API_KEY" not in blob
    assert "test-token" not in blob

    client.post(
        f"/api/trials/{trial_id}/annotate",
        json={"actual_source": "BOX_A_SECRET", "release_to_overlay": False},
        headers=auth_header,
    )
    public = client.get(f"/api/trials/{trial_id}").json()
    assert "BOX_A_SECRET" not in json.dumps(public)
    hidden = client.get(f"/api/trials/{trial_id}/ground-truth", headers=auth_header).json()
    assert hidden["disclosed"] is False
    client.post(
        f"/api/trials/{trial_id}/annotate",
        json={"actual_source": "BOX_A_SECRET", "release_to_overlay": True},
        headers=auth_header,
    )
    shown = client.get(f"/api/trials/{trial_id}/ground-truth", headers=auth_header).json()
    assert shown["actual_source"] == "BOX_A_SECRET"
    snapshot = client.get("/api/operations/snapshot").json()
    assert "BOX_A_SECRET" not in json.dumps(snapshot)
