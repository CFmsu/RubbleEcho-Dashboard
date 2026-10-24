# Architecture

RubbleEcho has two data planes.

The legacy plane is `backend/simulation.py`. It still serves `/api/mission/*` demo controls and `/ws/telemetry` for the 12×12 grid. That grid is always simulation.

The operations plane is `backend/app`. Drivers normalize samples. Fusion scores only acoustic and piezo evidence that was actually parsed. The heatmap lists measured points. A Nebius call, when enabled, receives event summaries and returns advisory JSON. `backend/app/services/policy.py` and `backend/app/drivers/solenoid.py` are the authorities for motion and knock requests. The model cannot set PWM, pins, or voltages.

Source mode is stored on each sample and device. Replay fixtures set `source_mode` to `replay`. A green system-live flag requires live mode plus live, connected radar, ultrasonic, microphone, and top camera. That flag is false for replay and for a disconnected dashboard.

Camera, serial, and USB audio adapters stay closed unless an operator sets a port or `RUBBLEECHO_PROBE_CAMERAS=1`. The default process does not open them.
