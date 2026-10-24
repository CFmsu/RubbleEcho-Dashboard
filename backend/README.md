# RubbleEcho Backend

The legacy simulation routes are unchanged. Operations routes, replay, export, and the Nebius client live in `app/`. See the repository README for setup.

Set `OPERATOR_TOKEN` before loading a replay or exporting a trial. `POST /api/mission/estop` does not require that token. It only stops and disarms software state. It does not replace a hardware e-stop.

## Legacy simulation

This is an in-memory simulation; it does not connect to rover hardware.
`main.py` exposes the API; `simulation.py` owns mission state and movement.

## Run

From this directory, create and activate a virtual environment, install the
dependencies, then start the API:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8081
```

Run the test suite from this directory with `pytest`.

## API And Telemetry

- `GET /api/health` returns `{"status":"ok"}`.
- `GET /api/scenarios` returns the earthquake, flood, and collapse presets.
- `POST /api/mission/start`, `/pause`, `/resume`, `/reset`, `/step`, and
  `/demo` control the in-memory mission. Start and demo accept
  `{"scenario":"collapse"}`; the scenario defaults to collapse.
- `WS /ws/telemetry` at `ws://localhost:8081/ws/telemetry` sends the telemetry object every 0.5 seconds. While the
  mission is active, each connection advances the shared simulation at most
  twice per second.

Yuni Lin's client reads these JSON fields:

| Field | Meaning |
| --- | --- |
| `mission.status` | `STANDBY`, `ACTIVE`, `PAUSED`, or `DONE` |
| `mission.phase` | `explore`, `knock`, `listen`, or `decide` |
| `mission.scenario` | Current scenario ID |
| `mission.probe_count` | Number of probes placed |
| `mission.confidence` | Confidence from the latest probe, from 0 to 1 |
| `robot.x`, `robot.y` | Rover grid position, each coordinate from 0 to 11 |
| `probes[]` | Probe `id`, `x`, `y`, and `confidence` |
| `events[]` | Recent human-readable simulation events |

The hidden source coordinate is never included in API or telemetry responses.
Demo mode uses the same five probe positions and confidence values each run.