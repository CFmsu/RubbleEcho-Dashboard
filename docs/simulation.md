# Simulation

This document describes how the prototype generates signals. None of these values are physical measurements.

## World

The environment is a continuous rectangle, typically 12 by 12 sector units. One hidden source coordinate is stored on the environment object. A deterministic debris field is generated from the scenario seed.

The same seed reproduces the same debris field and, for the probabilistic sensor model, the same reading at the same coordinate.

## Response model

Distance to the hidden source is converted to a proximity score:

```text
proximity = exp(-distance / 2.8)
```

From that score the simulator builds four features:

- audio confidence and an audio state
- vibration confidence
- cavity confidence
- visual confidence

Audio states are `NO_RESPONSE`, `AMBIENT_NOISE`, `WEAK_RESPONSE`, `POSSIBLE_TAP`, and `CONFIRMED_RESPONSE`. A tap is more likely when the probe is close, the configured response probability is high, and sensor reliability is high. Noise perturbs the vibration and cavity features.

## Waveforms

Piezo samples are a decaying knock impulse plus a later reflection whose size follows cavity confidence, plus a small noise floor.

Microphone samples are a noise floor. Tap states add short bursts so the chart can show a `tap … tap … tap` pattern. There is no speech recognition.

The camera adapter returns semantic fields only: surface type, debris density, whether a void is suggested, and whether the face looks safe to probe. The viewport in the dashboard is a synthetic frame, not a photograph.

## Fusion

Combined confidence is a weighted sum:

```text
audio 35% + vibration 30% + cavity 20% + visual 15%
```

This is an engineering explanation of the demo, not a validated detector.

## Belief map

The map starts uniform. After each probe, cells near the contact point are multiplied up or down based on how strong the combined observation was, then the map is normalized. Strong observations concentrate belief. Weak observations slightly suppress the area just searched.

## Search

Grid mode walks a serpentine survey with about 2 unit spacing.

Adaptive mode scores every open cell:

```text
score = 0.62 * probability + 0.22 * unexplored - 0.38 * travel
```

It will not immediately repeat a nearby probe.

## Demo mode

Demo mode uses a fixed five-probe path and fixed feature values so a briefing is reproducible. The same fusion function and belief update still run, so the heatmap changes for the same reason it does in autonomous mode. Demo mode is labeled on the dashboard.

## Comparison

The search-efficiency panel runs both strategies on the configured world inside the strategy simulator. Those figures are simulated results. They are not a claim about a physical robot.
