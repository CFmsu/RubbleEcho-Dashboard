# RubbleEcho

A search-and-rescue rover practice dashboard for the sand-table prototype, plus the original 12×12 software simulation.

This is not a certified rescue system. It does not locate real people, drive hardware by itself, or report a person as alive. Simulated and replayed values are labeled. A device is not marked live just because its card is on screen.

## What you can run today

- The legacy simulation: a 12×12 grid, mission controls, and `/ws/telemetry`.
- The sand-table operations view: Rev C geometry, camera slots, radar card, sensor cards, and trial export.
- A labeled replay fixture so the operations view can be demonstrated without sensors attached.
- A Nebius Token Factory client that stays offline until `NEBIUS_API_KEY`, `NEBIUS_MODEL_ID`, and `RUBBLEECHO_AI_LIVE=1` are set.

## Windows

From the repository root, in one terminal:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPERATOR_TOKEN = "choose-a-local-token"
uvicorn main:app --reload --port 8081
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually `http://localhost:5173/`. The API on port 8081 has no web page.

Paste the same operator token into the dashboard. Choose **Load replay** to play the fixture. Choose **STOP** for the software hold. A hardware e-stop still has to cut power.

Tests:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run build
npm run lint
```

## Raspberry Pi 4

Use a virtual environment. Do not install these packages into system Python on Raspberry Pi OS Bookworm without checking the OS packages first.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPERATOR_TOKEN=choose-a-local-token
uvicorn main:app --reload --port 8081
```

Start the frontend the same way as on Windows, or open a laptop browser against the Pi if you bind the servers deliberately. Hardware extras are listed in `backend/requirements-hardware.txt` and were not installed as part of the laptop test run. Install `opencv-contrib-python-headless` only. Do not also install `opencv-python`.

Optional live model check, after exporting the key and a catalog-confirmed NVIDIA model id:

```bash
export NEBIUS_API_KEY=...
export NEBIUS_MODEL_ID=...
export NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/
export RUBBLEECHO_AI_LIVE=1
py scripts/check_nebius.py --live
```

## Layout

- `backend/simulation.py` is the legacy demo.
- `backend/app` is the operations service.
- `shared/config/sand_table_rev_c.json` is the table geometry.
- `fixtures/replay/sample_trial` is synthetic replay data.
- `docs/` has the hardware checklist, validation protocol, and Devpost draft.

## License

MIT. See `LICENSE`. Confirm that choice with the team before a public submission.
