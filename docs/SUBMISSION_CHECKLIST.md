# Submission checklist

- [x] Single-viewport live console with centered square detail windows.
- [x] Rev C geometry, six named points, ground truth kept off the operator map.
- [x] Simulation and replay stay labeled. Live hardware stays disconnected until a driver reports it.
- [x] One camera card. No fabricated frame and no 360 degree label.
- [x] Audio detector returns `NOT_TRAINED` and does not score a heartbeat.
- [x] Mock Pi envelopes are synthetic and contain null measurements.
- [x] Scan fault stays latched until a person acknowledges it.
- [x] Nebius client exists and stays off without `AI_ENABLED` plus a local key.
- [ ] Physical Pi camera, `arecord -l`, and a real WAV.
- [ ] Uno ultrasonic acknowledgement and a bounded motor stop on the bench.
- [ ] MR60BHA2 fields from the attached kit.
- [ ] Supervised Mega knock with the pulse width measured, not assumed.
- [ ] Real NVIDIA catalog response from `/api/ai/healthcheck`.
- [ ] Held-out knock and control trials before any accuracy number.

Do not mark the open boxes from a Windows session.
