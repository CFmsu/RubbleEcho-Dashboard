# Devpost draft

Do not submit invented results. Replace every PLACEHOLDER.

## Name

RubbleEcho

## Tagline

A sand-table rover dashboard that keeps simulated, replayed, and live sensor evidence separate, and asks an NVIDIA model on Nebius only for advice.

## Inspiration

Search-and-rescue teams need a way to practice sensing before anyone trusts a machine in rubble. The team is building that practice around a measured sand table rather than a decorative grid.

## What it does

The dashboard shows the Rev C sand table, three camera slots, a 60 GHz radar card, obstacle distance, microphone and piezo events, and a trial export. The original 12×12 mission still runs and is labeled simulation. A replay fixture demonstrates the operations view without pretending the laptop is the rover.

## How we built it

React and Vite on the frontend. FastAPI on the backend. Geometry lives in one JSON file. Safety and knock gating are deterministic Python. The Nebius client uses the OpenAI-compatible Token Factory API and an operator-selected NVIDIA model id.

## Challenges

The drawing PDF was not in the repository, so coordinates are plan inferences. Device firmware, pinouts, and camera types were not on the bench. The software refuses to fill those gaps with fake telemetry.

## Accomplishments

Software tests cover the legacy simulation, geometry, replay labeling, radar parsing, export contents, and the safety interlock. Hardware detection metrics are not accomplishments yet.

## What we learned

A listen step in a demo is not a microphone. The UI has to say which of those it is.

## What's next

Wire the verified sensors, calibrate ArUco markers, run the silence and knock protocol, and enable the live Nebius call.

## Built with

Python, FastAPI, React, TypeScript, Vite, and, when a key is configured, Nebius Token Factory.

## NVIDIA evidence

Model id: PLACEHOLDER after `GET /v1/models` and a successful `scripts/check_nebius.py --live` run.

Repository: https://github.com/CFmsu/RubbleEcho-Dashboard

Video: PLACEHOLDER

Team members: PLACEHOLDER. Confirm the roster with the project lead. Do not invent names.

## Feedback

ACTUAL OBSERVATION REQUIRED.
