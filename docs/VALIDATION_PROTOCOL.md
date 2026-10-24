# Validation protocol

These trials have not been run on the sand table. Do not publish the numbers below as results.

For each cover setting (about 10 cm and about 5 cm of sand above the lids) and each near/far point of boxes A, B, and C:

1. Record at least 10 seconds of silence with the rover stopped and motors off.
2. Record 10 commanded knocks. Pulse width stays at or below 40 ms. Onset spacing is 250 ms. Do not hold the coil on for 250 ms.
3. Repeat a separate scratch or scrape series. Do not mix it into the knock counts.
4. Repeat with motors running so self-noise is a separate condition.
5. Score B and C as control boxes. A louder A does not prove a person is present.
6. Keep the active-source label out of the live snapshot until scoring. Enter it with the annotate API when the operator is ready to release the overlay.

`scripts/evaluate_trials.py` computes precision and recall only from pairs you pass in. With no pairs it prints `labeled hardware metrics: not measured`.

The continuous plywood top can couple vibration between boxes. If control points trigger with the source, record that limit instead of tightening a threshold until the control goes silent.
