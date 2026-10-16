# Hardware roadmap

RubbleEcho is in Phase 1. Later phases replace simulated adapters. They do not require a new dashboard.

## Phase 1 — Software simulation

Mission logic, synthetic sensors, belief map, adaptive search, and the mission-control interface. This repository.

## Phase 2 — Individual sensor bench tests

Microphone, piezo, and striker on a bench. Compare recorded waveforms with the synthetic shapes used here. Keep the sensor-lab page as the viewer.

## Phase 3 — ESP32 / microcontroller integration

Replace `SimulatedMotionAdapter`, `SimulatedPiezoAdapter`, and `SimulatedStrikerAdapter` with serial or GPIO adapters. The mission controller should keep calling the same methods.

## Phase 4 — Mobile robot integration

Mount the striker, microphone, piezo, and camera on a mobility platform. `ESP32MotionAdapter` reports pose into the same robot state the dashboard already renders.

## Phase 5 — Local edge processing

Move waveform features and the first fusion pass onto the robot computer. The backend can receive features instead of synthesizing them.

## Phase 6 — NVIDIA / Nebius AI integration

`NvidiaReasoningAdapter` and `NebiusInferenceAdapter` call the configured model host when `NEBIUS_API_KEY` is set. The field page uses an image model for photographs and a text model for sector recommendations. The simulated mission loop still uses `SimulatedReasoningProvider` and does not send mock probes to that host.

## Phase 7 — Controlled rubble test environment

Repeat the knock-listen-update loop in a built debris volume with a known, safe target. Record probes, travel, and false prompts. Do not treat earlier simulation numbers as the result of this phase.

## Phase 8 — Integrated demonstration

One robot, one belief map, one candidate location handed to a rescue team for verification. RubbleEcho still locates a candidate. People perform the rescue.

## Suggested branches

```text
main
develop
frontend/dashboard
backend/simulation
hardware/integration
ai/reasoning
```

For a small team, use short feature branches and pull requests. Avoid extra process beyond that.
