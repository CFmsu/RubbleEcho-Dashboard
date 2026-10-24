# Sensor protocols

See `firmware/protocols/README.md` for the CRC frame and line prefixes.

## MR60BHA2

The intended microcontroller path is the Seeed library: `isHumanDetected`, `getBreathRate`, `getHeartRate`, `getHeartBreathPhases`, and `getDistance`. The bridge prints `RADAR` plus JSON. This repository does not parse an unverified binary frame.

Breath and heart values are dropped when stability is not `stationary`, when the sample is stale, or when a retained-value flag is set. Target XY is kept only if `spatial_coordinates_supported` is true. Otherwise the UI draws no blip.

Through-sand vital signs are not a claim.

## HC-SR04

The contract unit is centimeters. Values outside 2–400 cm are marked out of range. A timeout becomes "not clear", not a free path. The reading is obstacle distance in the sensor's facing direction.

## XVF3800

Channel count and sample rate must come from the host audio API. This build does not open a device and does not guess a 4-mic layout. DSP thresholds in `feature_extraction.py` are uncalibrated. Levels are dBFS, not dB SPL. The classifier does not emit a speech class.

## Piezo

Values stay in ADC counts. There is no conversion to g. Clipping is reported only when the sample says it clipped, because full-scale voltage was not measured.

## Solenoid

States are `DISARMED`, `ARMED`, `COOLDOWN`, and `FAULT`. Default is disarmed. A software accept still sets `output_energized` false.
