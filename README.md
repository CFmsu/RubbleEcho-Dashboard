# RubbleEcho

A search-and-rescue rover practice dashboard for the sand-table prototype, plus the original 12×12 software simulation.

This is not a certified rescue system. It does not locate real people, drive hardware by itself, or report a person as alive. Simulated and replayed values are labeled. A device is not marked live just because its card is on screen.

## What you can run today

- The legacy simulation: a 12×12 grid, mission controls, and `/ws/telemetry`.
- The sand-table operations view: a single-viewport Rev C console. Detail dialogs hold the longer diagnostics. Disconnected sensors stay blank.
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

Open the Vite URL, usually `http://localhost:5173/`. The API on port 8081 has no web page. The live console fits a 1440×900 desktop without page scrolling.

Open Help if you need About, How it works, Architecture, or the legacy 12×12 simulation. Open Diagnostics from the device count to paste the operator token. Choose **Load replay** to play the fixture. **STOP** in the header is the software stop. A hardware e-stop still has to cut power. Start Scan stays disabled until the live health policy passes, and it does not command motors.

Tests:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run build
npm run lint
npm run test:e2e
```

`npm run test:e2e` starts Vite and checks the live console at 1920×1080, 1440×900, and 1366×768. The API should already be on port 8081. The first run downloads Chromium.

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
