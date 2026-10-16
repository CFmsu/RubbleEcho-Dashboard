# RubbleEcho

A dashboard for the RubbleEcho rover project for the ACM 2026 hackathon.

Developed by **McNeeseNexus**.

## Overview

RubbleEcho is a search-and-rescue robotics project. The robot is meant to move through debris, stop, knock, and use the vibration and sound that come back to decide where to look next.

This repository is the first software prototype: a mission-control dashboard driven by a simulated robot. It does not control hardware.

```text
Current version: simulation prototype
```

## Problem

After an earthquake, flood, or collapse, the searchable volume is large and much of it is hidden. A search that treats every point the same spends time where there is no evidence. Passive listening also misses people who can only answer when something prompts them.

## Concept

RubbleEcho is an active-sensing loop:

1. Explore a sector.
2. Stop on a contact face.
3. Knock.
4. Listen and measure vibration.
5. Fuse those signals into a simulated confidence.
6. Update a spatial belief map.
7. Choose the next probe from that map.
8. Repeat until a response is strong enough to confirm.
9. Mark a candidate location for a rescue team to verify.

The system locates a candidate. It does not perform the rescue.

## Current status

| Piece | State |
| --- | --- |
| Simulation engine | Running |
| Mission dashboard | Running |
| Adaptive search | Prototype |
| Physical robot, piezo, microphone, striker | Not connected |
| NVIDIA and Nebius | Placeholder adapters only |
| Field validation | Not started |

The interface is labeled **SIMULATION MODE**. Charts are synthetic signals. Confidence is an engineering estimate, not a life-safety measurement.

## Architecture

```text
Browser
  → React mission control
  → REST + WebSocket
  → FastAPI mission controller
  → Simulation engine
  → Belief map and search strategy
  → Telemetry
```

The hidden source coordinate stays inside the environment simulator. The search code only sees sensor features. Hardware and model providers sit behind adapters so later ESP32, camera, piezo, NVIDIA, or Nebius code can replace a simulator without rewriting the dashboard.

See [docs/architecture.md](docs/architecture.md).

## Features

- Dark mission-control dashboard for a 1920×1080 presentation screen
- Live search map with robot trail, probes, and a probability heatmap
- Knock → listen → analyze timeline
- Synthetic piezo and microphone charts
- Sensor fusion from the simulated knock and listen signals
- Grid search and adaptive search, with a simulated comparison
- Reproducible demo mode
- Sensor lab for manual stimuli
- Scenario setup, including presets inspired by earthquake, flood, and collapse conditions
- WebSocket telemetry with automatic reconnect
- Keyboard controls: Space pause, `N` step, `R` reset, `P` presentation, `D` demo

## Technology stack

Frontend: React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide.

Backend: Python 3.11+, FastAPI, Pydantic, Uvicorn, WebSockets, NumPy.

Mission state is in memory. A completed mission can also be written to `backend/data/`, which is gitignored. PostgreSQL is not required.

## Installation

Use two terminals from the repository root.

### Running the backend

```bash
cd backend

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

uvicorn main:app --reload --port 8080
```

The API is at `http://127.0.0.1:8080`. Health check: `http://127.0.0.1:8080/api/health`. Interactive docs: `http://127.0.0.1:8080/docs`.

Port 8080 is used because port 8000 is often reserved by Windows. Inside Docker the same port is published.

### Running the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The dev server proxies `/api` and `/ws` to the backend.

On Windows you can also run `scripts/start-dev.ps1` after the virtual environment and `npm install` already exist. `scripts/start-dev.sh` does the same on macOS or Linux.

The Field page is the hardware path: photographs, optional cloud models, and the serial test. Setup and the sketches are in [docs/physical-prototype.md](docs/physical-prototype.md). Copy `.env.example` to `.env` and add `NEBIUS_API_KEY` only when you want a live model call. Leave the ultrasonic flag false until an HC-SR04 is wired.

Optional: the prototype's simulated mission runs with the keys empty.

## Simulation

A scenario is a rectangle, usually 12×12 sector units, with one hidden source. Probes closer to that source tend to return stronger vibration, a stronger cavity hint, and eventually a tap-like audio pattern. Noise keeps a single probe from solving the map.

Demo mode uses a fixed five-probe path and fixed features so a briefing is repeatable. Fusion and the belief map are the same code paths as autonomous search. The dashboard marks demo mode.

The search-efficiency numbers are produced by a strategy simulator on the same seeded world. They are labeled **simulated results**.

Details: [docs/simulation.md](docs/simulation.md). A three-minute talk track is in [docs/demo-script.md](docs/demo-script.md).

## Future hardware integration

Planned adapter swap, not a rewrite:

| Interface | Now | Later |
| --- | --- | --- |
| `MotionAdapter` | Simulated motion | ESP32 / chassis |
| `CameraAdapter` | Semantic placeholder | USB camera and a vision model |
| `MicrophoneAdapter` | Synthetic waveform | Microphone capture |
| `PiezoAdapter` | Synthetic waveform | Serial piezo |
| `StrikerAdapter` | Simulated solenoid | GPIO striker |
| `ReasoningProvider` | Template text | Optional cloud model |

Stages are listed in [docs/hardware-roadmap.md](docs/hardware-roadmap.md).

## Optional model calls

The simulated mission does not call an external model. The Field page can, when `NEBIUS_API_KEY` is set in `.env`. Do not commit that file.

Until a key is set, the decision panel says **Decision source: SIMULATED**.

## Tests

From `backend`, with the virtual environment active:

```bash
pytest
```

Tests cover deterministic seeds, sensor generation, belief-map updates, next-probe selection, mission pause/reset, the demo outcome, and the health endpoint. They are regression checks, not a scientific validation.

## Suggested branches

```text
main
develop
frontend/dashboard
backend/simulation
hardware/integration
ai/reasoning
```

Short feature branches and pull requests are enough for a small team.

## Safety / scope

This repository is currently an experimental research and hackathon prototype. Simulation outputs are not validated life-safety measurements and should not be used for operational rescue decisions.

## Team

McNeeseNexus
