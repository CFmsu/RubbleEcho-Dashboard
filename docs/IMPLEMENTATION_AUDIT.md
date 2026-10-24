# Implementation audit

Audit date: 2026-10-23. Starting commit on `main`: `bb1e622` (`Merge pull request #3 from CFmsu/pratikshya-backend-integration`).

## What was already in the repository

- `backend/main.py` served FastAPI on port 8081 with health, scenario, mission, and `/ws/telemetry` routes.
- `backend/simulation.py` ran a 12×12 in-memory mission: explore, knock, listen, decide. Confidence came from distance to a hidden coordinate that was not sent to the client.
- `backend/test_main.py` covered health, repeatable demo, pause, and reset.
- The frontend was React, TypeScript, and Vite. `vite.config.ts` proxied `/api` and `/ws` to `127.0.0.1:8081`.
- Pages were Live Run, How It Works, About, and Architecture.
- There was no LICENSE file, no physical sensor adapter, no sand-table geometry file, and no Nebius client.
- `Sand table setup (1).pdf` was not in the checkout. Geometry in `shared/config/sand_table_rev_c.json` uses the measurements supplied with the implementation brief and is marked pending a physical survey.

## What this branch adds

- A typed operations snapshot with source modes `live`, `replay`, `simulation`, `manual`, and `unavailable`.
- The legacy simulation routes and `/ws/telemetry` payload shape are unchanged.
- New state is on `/ws/operations` and `/api/operations/snapshot`.
- Replay fixture `fixtures/replay/sample_trial` is labeled replay. It does not mark cameras, motors, or NVIDIA online.
- Safety policy, solenoid interlock, trial export, and a Nebius client that stays `NOT_CONFIGURED` without a key.

## Compatibility choice

`/ws/telemetry` still emits exactly `mission`, `robot`, `probes`, and `events` because the existing test requires that set. Versioned physical and replay updates use `/ws/operations`.
