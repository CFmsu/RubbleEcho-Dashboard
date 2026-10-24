# Safety and limitations

This is a prototype. It is not a certified rescue device, medical device, or vital-signs monitor.

- The local safety policy can reject a move. It does not replace a hardware emergency stop.
- Cloud failure, invalid model JSON, a duplicate command, a missing echo, an obstacle inside the stop margin, a stale pose, and an encoder timeout hold motion and disarm the knock request. They do not energize hardware.
- The model recommendation allowlist is `stop`, `rescan_at_point`, `capture`, `settle_and_listen`, and `needs_operator`. `move_cm` from the model is rejected.
- Radar, microphones, and the piezo do not see through sand in any validated way in this software.
- The hidden evaluation label is not an input to fusion. The replay file `ground_truth.json` is not loaded by the replay player.
- Heatmap colors are heuristic scores at measured points.
- Default stop and caution distances are conservative placeholders until the rover is measured.
