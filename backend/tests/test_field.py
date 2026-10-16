import io
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from core.state import controller
from field.grid import CELL_IDS, cell_at, cell_bounds
from field.models_catalog import ModelInfo, accepts_images, select_reasoning_model, select_vision_model
from field.schema import validate_reasoning, validate_vision
from field.store import store
from hardware.serial_bridge import EventLog, SerialBridge, parse_serial_line
from integrations.nebius.client import NebiusClient
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "")
    monkeypatch.setenv("RUBBLEECHO_ULTRASONIC_ENABLED", "")
    store.configure(tmp_path)
    store.reset()
    from hardware.serial_bridge import bridge

    bridge.log.reset()
    bridge._on_change = lambda: None
    bridge.disconnect()
    bridge.set_ultrasonic_enabled(True)
    with TestClient(app) as test_client:
        yield test_client
    store.set_operating_mode("demo")
    bridge.log.reset()
    bridge.disconnect()
    controller.reset()


def _png_bytes() -> bytes:
    image = Image.new("RGB", (40, 20), (180, 90, 40))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _cells(classification: str = "uncertain", observation: str = "rubble is visible") -> list[dict]:
    return [
        {
            "cell": cell_id,
            "classification": classification,
            "observation": observation,
            "uncertainty": "high",
        }
        for cell_id in CELL_IDS
    ]


def test_grid_maps_corners_and_edges():
    assert cell_at(0, 0) == "A1"
    assert cell_at(0.24, 0) == "A1"
    assert cell_at(0.25, 0) == "B1"
    assert cell_at(0.99, 0) == "D1"
    assert cell_at(0, 0.25) == "A2"
    assert cell_at(1, 1) == "D4"
    assert cell_bounds("A1") == {"left": 0.0, "top": 0.0, "right": 0.25, "bottom": 0.25}
    assert cell_bounds("D4")["left"] == 0.75
    assert cell_bounds("D4")["top"] == 0.75
    with pytest.raises(ValueError):
        cell_at(1.1, 0)
    with pytest.raises(ValueError):
        cell_bounds("E1")


def test_vision_schema_accepts_sixteen_cells_and_rejects_extra_claims():
    payload = validate_vision(json.dumps({"cells": _cells(), "summary": "Surface rubble is visible.", "limitations": []}))
    assert [cell.cell for cell in payload.cells] == list(CELL_IDS)
    assert "photograph cannot reveal" in payload.limitations[-1]
    broken = {"cells": _cells()[:-1], "summary": "incomplete", "limitations": []}
    with pytest.raises(ValueError):
        validate_vision(json.dumps(broken))
    extra = {"cells": _cells(), "summary": "no", "limitations": [], "survivor_detected": True}
    with pytest.raises(ValueError):
        validate_vision(json.dumps(extra))
    claimed = {"cells": _cells(observation="survivor detected under the slab"), "summary": "no", "limitations": []}
    with pytest.raises(ValueError):
        validate_vision(json.dumps(claimed))


def test_reasoning_schema_rejects_a_confidence_field():
    body = {
        "priorities": [
            {
                "cell": "B2",
                "priority": 1,
                "reason": "The cell looks obstructed.",
                "evidence": ["a slab covers the surface"],
                "uncertainty": "The photo cannot show what is behind the slab.",
                "next_action": "Look at sector B2 from another angle.",
            }
        ],
        "uncertainties": ["lighting is uneven"],
        "cannot_infer": ["buried survivors"],
    }
    parsed = validate_reasoning(json.dumps(body))
    assert "vital signs" in parsed.cannot_infer
    body["priorities"][0]["confidence"] = 0.9
    with pytest.raises(ValueError):
        validate_reasoning(json.dumps(body))


def test_model_selection_does_not_treat_nemotron_as_a_vision_model():
    lightning = ModelInfo(id="nvidia/Nemotron-3_5-Lightning")
    qwen = ModelInfo(id="Qwen/Qwen2-VL-72B-Instruct")
    omni = ModelInfo(id="nvidia/nemotron-omni", input_modalities=("image", "text"))
    gemma = ModelInfo(id="google/gemma-3-27b-it")
    minicpm = ModelInfo(id="openbmb/MiniCPM-V-4_5")
    assert accepts_images(lightning) is False
    assert accepts_images(qwen) is True
    assert accepts_images(omni) is True
    assert accepts_images(gemma) is False
    assert accepts_images(minicpm) is True
    assert select_vision_model([lightning, gemma, minicpm], None).id == minicpm.id
    with pytest.raises(LookupError):
        select_vision_model([lightning], "nvidia/Nemotron-3_5-Lightning")
    assert select_reasoning_model([ModelInfo(id="nvidia/nemotron-3-super"), lightning], None).id == lightning.id


def test_invalid_model_json_is_not_stored_as_findings():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "Qwen/Qwen2-VL-72B-Instruct"}, {"id": "nvidia/Nemotron-3_5-Lightning"}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "this is not json"}}]})

    from field.inference import analyze_image

    result = analyze_image(b"jpeg", "image/jpeg", client=NebiusClient(api_key="test-key", transport=httpx.MockTransport(handler)))
    assert result.request_status == "failed"
    assert result.cells == []
    assert "JSON" in (result.error or "")


def test_image_upload_saves_original_and_aligned_grid(client: TestClient):
    response = client.post(
        "/api/observations",
        files={"file": ("iphone.png", _png_bytes(), "image/png")},
        data={"source": "iphone_camera"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "iphone_camera"
    assert body["width"] == 40
    assert body["height"] == 20
    assert [cell["cell"] for cell in body["cells"]] == list(CELL_IDS)
    assert all(cell["source"] == "unanalyzed" for cell in body["cells"])
    image = client.get(f"/api/observations/{body['id']}/image")
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/jpeg")
    folder = store.root / "observations" / body["id"]
    assert (folder / "original.png").exists()
    assert (folder / "display.jpg").exists()
    assert json.loads((folder / "meta.json").read_text(encoding="utf-8"))["id"] == body["id"]


def test_analyze_without_a_key_keeps_manual_labels(client: TestClient):
    created = client.post(
        "/api/observations",
        files={"file": ("iphone.png", _png_bytes(), "image/png")},
        data={"source": "iphone_camera"},
    ).json()
    corrected = client.post(
        f"/api/observations/{created['id']}/cells",
        json={"cell": "C3", "classification": "possible_opening", "observation": "A dark gap is visible.", "uncertainty": "medium"},
    )
    assert corrected.status_code == 200
    assert corrected.json()["cells"][10]["source"] == "manual_correction"
    analyzed = client.post(f"/api/observations/{created['id']}/analyze")
    assert analyzed.status_code == 200
    analysis = analyzed.json()["analysis"]
    assert analysis["request_status"] == "failed"
    assert "NEBIUS_API_KEY" in analysis["error"]
    kept = next(cell for cell in analyzed.json()["cells"] if cell["cell"] == "C3")
    assert kept["source"] == "manual_correction"
    assert kept["classification"] == "possible_opening"
    reasoned = client.post(f"/api/observations/{created['id']}/reason")
    assert reasoned.json()["reasoning"]["request_status"] == "failed"
    assert reasoned.json()["reasoning"]["priorities"] == []


def test_serial_parse_dedup_and_disconnect():
    line = '{"device_id":"esp32-wroom-32","event_id":"esp32-wroom-32-1","event_type":"boot_button","sequence":1,"uptime_ms":40}'
    parsed = parse_serial_line(line)
    assert parsed.event is not None
    assert parsed.event["event_type"] == "boot_button"
    assert parse_serial_line("boot noise").event is None

    class FakePort:
        def __init__(self) -> None:
            self.lines = [line.encode() + b"\n", line.encode() + b"\n"]
            self.closed = False

        def readline(self) -> bytes:
            if self.closed:
                raise OSError("closed")
            if self.lines:
                return self.lines.pop(0)
            raise OSError("unplugged")

        def close(self) -> None:
            self.closed = True

    log = EventLog()
    bridge = SerialBridge(log, on_change=lambda: None)
    bridge.connect("COM99", opener=lambda _name: FakePort())
    deadline = time.time() + 2
    while time.time() < deadline and not (bridge.state == "DISCONNECTED" and len(log.events) == 1):
        time.sleep(0.02)
    assert bridge.state == "DISCONNECTED"
    assert len(log.events) == 1
    assert log.events[0].label == "MANUAL_HARDWARE_TEST"
    before = len(log.events)
    time.sleep(0.05)
    assert len(log.events) == before


def test_plain_distance_text_keeps_exact_centimeters_in_order():
    log = EventLog()
    local = SerialBridge(log, on_change=lambda: None)
    assert local.inject_line("Distance: 25 cm") == "distance"
    assert local.inject_line("Distance: 11 cm") == "distance"
    assert local.inject_line("Distance: 48.5 cm") == "distance"
    assert local.inject_line("The nearest detected object is 65.84 cm away.") == "distance"
    assert local.log.distances[-1].distance_cm == 65.84
    assert [item.distance_cm for item in log.distances] == [25.0, 11.0, 48.5, 65.84]
    assert [item.sequence for item in log.distances] == [1, 2, 3, 4]
    assert all(item.source == "REAL_HARDWARE" and item.sensor_id == "hc-sr04" for item in log.distances)
    local.disconnect()
    assert local.snapshot()["link_status"] == "DISCONNECTED"
    assert len(log.distances) == 4


def test_bench_json_is_not_stored_as_an_ultrasonic_reading():
    log = EventLog()
    local = SerialBridge(log, on_change=lambda: None)
    local.state = "CONNECTED"
    assert local.snapshot()["bench_status"] == "WAITING"
    frame = (
        '{"ms":1000,"flex_raw":512,"light_pocket_raw":300,"light_reference_raw":700,'
        '"thermistor_raw":480,"pir_left":null,"pir_right":null,"pir_ready":false,'
        '"heading_deg":null,"range_pw_us":2940,"range_cm":50.8,"range_status":"ok"}'
    )
    assert local.inject_line(frame) == "bench"
    assert log.distances == []
    sample = log.bench[-1]
    assert sample.source == "REAL_HARDWARE"
    assert sample.flex_raw == 512
    assert sample.light_pocket_raw == 300
    assert sample.thermistor_raw == 480
    assert sample.pir_left is None
    assert sample.pir_right is None
    assert sample.heading_deg is None
    assert sample.range_cm == 50.8
    assert sample.range_status == "ok"
    assert local.snapshot()["bench_status"] == "CONNECTED"
    stale = (
        '{"ms":1100,"flex_raw":500,"light_pocket_raw":100,"light_reference_raw":690,'
        '"thermistor_raw":481,"pir_left":null,"pir_right":null,"pir_ready":false,'
        '"heading_deg":null,"range_pw_us":null,"range_cm":null,"range_status":"stale_or_invalid"}'
    )
    assert local.inject_line(stale) == "bench"
    assert log.bench[-1].range_cm is None
    assert log.bench[-1].range_pw_us is None
    assert local.inject_line("The nearest detected object is 65.84 cm away.") == "distance"
    assert [item.distance_cm for item in log.distances] == [65.84]
    assert len(log.bench) == 2
    log.bench[-1].timestamp = "2000-01-01T00:00:00+00:00"
    assert local.snapshot()["bench_status"] == "STALE"
    local.disconnect()
    assert local.snapshot()["bench_status"] == "DISCONNECTED"
    assert len(log.bench) == 2
    assert len(log.distances) == 1


def test_demo_mission_does_not_enter_the_real_event_log(client: TestClient):
    controller.start(demo=True)
    controller.tick(0.2)
    client.post("/api/mode", json={"operating_mode": "real"})
    field = client.get("/api/field").json()
    telemetry = controller.snapshot().model_dump()
    assert field["operating_mode"] == "real"
    assert field["observations"] == []
    assert field["hardware"]["events"] == []
    assert field["hardware"]["bench"] == []
    assert field["hardware"]["state"] == "DISCONNECTED"
    assert telemetry["mode"] == "simulation"
    health = client.get("/api/health").json()
    assert health["mode"] == "real"
    assert health["operating_mode"] == "real"
    client.post("/api/mode", json={"operating_mode": "demo"})
    assert client.get("/api/health").json()["mode"] == "simulation"


def test_field_snapshot_matches_the_stored_observation(client: TestClient):
    created = client.post(
        "/api/observations",
        files={"file": ("iphone.png", _png_bytes(), "image/png")},
        data={"source": "iphone_camera"},
    ).json()
    field = client.get("/api/field").json()
    assert field["type"] == "field"
    assert field["observations"][0]["id"] == created["id"]
    assert field["observations"][0]["source"] == "iphone_camera"
    assert "photograph cannot reveal" in " ".join(field["warnings"]).lower() or any(
        "photograph" in warning.lower() for warning in field["warnings"]
    )
