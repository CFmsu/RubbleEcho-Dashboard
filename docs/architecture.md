# Architecture

RubbleEcho separates the mission-control interface from the simulation so a later hardware build can replace simulators without rewriting the dashboard.

## Data flow

```text
Browser
  → React mission control
  → REST + WebSocket
  → FastAPI
  → Mission controller
  → Simulation engine
      Robot, environment, acoustic, piezo, camera, striker, survivor response
  → Search strategy
  → Probability map
  → Next probe
  → Telemetry back to the dashboard
```

The hidden source coordinate lives on `Environment`. Search strategy and the probability map never receive it. Sensor simulators are the only path from that coordinate to an observation.

Field observations use a separate store and `/ws/field`. Photographs, Nebius responses, and ESP32 serial events never enter the simulated telemetry snapshot. See [physical-prototype.md](physical-prototype.md).

## Backend modules

| Module | Responsibility |
| --- | --- |
| `core/mission_controller.py` | Probe state machine, event log, snapshots |
| `core/simulation_engine.py` | World, belief map, and one measurement |
| `core/search_strategy.py` | Grid and adaptive probe selection |
| `reasoning/probability_map.py` | Spatial belief update |
| `reasoning/sensor_fusion.py` | Explainable weighted confidence |
| `reasoning/provider.py` | `ReasoningProvider` interface and the simulated provider |
| `adapters/` | Motion, camera, microphone, piezo, and striker seams |
| `integrations/nvidia/` | Placeholder for a future NVIDIA reasoning adapter |
| `integrations/nebius/` | Placeholder for a future Nebius inference adapter |

## Frontend modules

The dashboard is a client of the telemetry snapshot. Pages do not generate the mission. `services/api.ts` and `services/websocket.ts` are the only network boundary.

## Current and future implementation

Current implementation: simulation.

Future implementation: physical sensors, an edge computer, and NVIDIA or Nebius inference behind the existing adapter interfaces. The WebSocket payload shape can stay stable while those adapters change.
