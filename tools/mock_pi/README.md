# Mock Pi packets

`mock_raspberry_pi.py` writes 24 JSON envelopes, four for each of A_NEAR, A_FAR, B_NEAR, B_FAR, C_NEAR, and C_FAR.

Every envelope has `mode` `SIMULATION` and `synthetic` true. Distances, audio scores, and radar fields are null. Do not use these packets as training labels or as live evidence.

```powershell
python tools\mock_pi\mock_raspberry_pi.py
```
