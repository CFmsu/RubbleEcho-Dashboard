"""Report whether the XVF3800 raw stream is enumerated. Does not open a capture."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.drivers.respeaker import device_report

report = device_report()
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["state"] == "ready" else 2)
