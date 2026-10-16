"""USB serial bridge for the ESP32 BOOT-button experiment.

Events are accepted only from the serial port the operator connected.
When that port closes or disappears, the state becomes DISCONNECTED and
the reader stops. Nothing is synthesized to fill the gap.
"""

from __future__ import annotations

import json
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

_REQUIRED = ("device_id", "event_id", "event_type", "sequence", "uptime_ms")
_PLAIN_DISTANCE = re.compile(r"(?i)^\s*distance\s*[:=]\s*(?P<value>\d+(?:\.\d+)?)\s*(?:cm)?\s*$")
_CM_VALUE = re.compile(r"(?i)(?P<value>\d+(?:\.\d+)?)\s*cm\b")
ALLOWED_BAUD = (9600, 19200, 38400, 57600, 115200)
STALE_AFTER_S = 3.0


class HardwareEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    device_id: str
    event_id: str
    event_type: str
    sequence: int = Field(ge=0)
    uptime_ms: int = Field(ge=0)
    label: str = "MANUAL_HARDWARE_TEST"
    received_at: str
    port: str


class BenchSample(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: Literal["REAL_HARDWARE"] = "REAL_HARDWARE"
    sensor_id: str = "uno-multisensor"
    sequence: int
    timestamp: str
    device_ms: int | None = None
    flex_raw: int | None = None
    light_pocket_raw: int | None = None
    light_reference_raw: int | None = None
    thermistor_raw: int | None = None
    pir_left: int | None = None
    pir_right: int | None = None
    pir_ready: bool | None = None
    heading_deg: float | None = None
    range_pw_us: int | None = None
    range_cm: float | None = None
    range_status: str | None = None


class DistanceReading(BaseModel):
    model_config = ConfigDict(extra="allow")

    sensor_id: str = "hc-sr04"
    source: Literal["REAL_HARDWARE"] = "REAL_HARDWARE"
    distance_cm: float | None = None
    timestamp: str
    sequence: int
    received_at: str
    port: str
    device_id: str = "hc-sr04"
    event_id: str
    event_type: str = "distance_cm"
    valid: bool = True
    uptime_ms: int | None = None


class SerialPortInfo(BaseModel):
    device: str
    description: str
    hwid: str = ""


class LinePort(Protocol):
    def readline(self) -> bytes: ...

    def close(self) -> None: ...


@dataclass
class ParseResult:
    event: dict | None
    error: str | None = None


def parse_serial_line(line: str) -> ParseResult:
    text = line.strip()
    if not text:
        return ParseResult(event=None)
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return ParseResult(event=None, error="ignored serial line")
        if not isinstance(payload, dict):
            return ParseResult(event=None, error="ignored non-object serial line")
        if "flex_raw" in payload or "light_pocket_raw" in payload:
            payload["event_type"] = "bench_sample"
            return ParseResult(event=payload)
        if payload.get("event_type") == "distance_cm" or "distance_cm" in payload:
            payload["event_type"] = "distance_cm"
            payload["source"] = "REAL_HARDWARE"
            payload.setdefault("sensor_id", "hc-sr04")
            payload.setdefault("device_id", payload.get("sensor_id", "hc-sr04"))
            return ParseResult(event=payload)
        missing = [key for key in _REQUIRED if key not in payload]
        if missing:
            return ParseResult(event=None, error=f"serial JSON missing {', '.join(missing)}")
        return ParseResult(event=payload)
    plain = _PLAIN_DISTANCE.match(text) or _CM_VALUE.search(text)
    if plain:
        return ParseResult(
            event={
                "sensor_id": "hc-sr04",
                "device_id": "hc-sr04",
                "event_type": "distance_cm",
                "distance_cm": float(plain.group("value")),
                "source": "REAL_HARDWARE",
                "valid": True,
            }
        )
    return ParseResult(event=None, error="ignored serial line")


class EventLog:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.events: list[HardwareEvent] = []
        self.distances: list[DistanceReading] = []
        self.bench: list[BenchSample] = []
        self._ids: set[str] = set()
        self._distance_sequence = 0
        self._bench_sequence = 0
        self.ignored_notes: list[str] = []

    def reset(self) -> None:
        with self._lock:
            self.events.clear()
            self.distances.clear()
            self.bench.clear()
            self._ids.clear()
            self._distance_sequence = 0
            self._bench_sequence = 0
            self.ignored_notes.clear()

    def add(self, payload: dict, *, port: str, received_at: str, ultrasonic_enabled: bool) -> str:
        """Return 'event', 'duplicate', 'distance', 'ignored', or 'invalid'."""
        event_id = str(payload.get("event_id", ""))
        event_type = str(payload.get("event_type", ""))
        with self._lock:
            if event_type == "bench_sample":
                self._bench_sequence += 1
                try:
                    sample = BenchSample.model_validate(
                        {
                            "source": "REAL_HARDWARE",
                            "sensor_id": "uno-multisensor",
                            "sequence": self._bench_sequence,
                            "timestamp": received_at,
                            "device_ms": payload.get("ms"),
                            "flex_raw": payload.get("flex_raw"),
                            "light_pocket_raw": payload.get("light_pocket_raw"),
                            "light_reference_raw": payload.get("light_reference_raw"),
                            "thermistor_raw": payload.get("thermistor_raw"),
                            "pir_left": payload.get("pir_left"),
                            "pir_right": payload.get("pir_right"),
                            "pir_ready": payload.get("pir_ready"),
                            "heading_deg": payload.get("heading_deg"),
                            "range_pw_us": payload.get("range_pw_us"),
                            "range_cm": payload.get("range_cm"),
                            "range_status": payload.get("range_status"),
                        }
                    )
                except (ValidationError, TypeError, ValueError):
                    self._bench_sequence -= 1
                    return "invalid"
                self.bench.append(sample)
                self.bench[:] = self.bench[-300:]
                return "bench"
            if event_type == "distance_cm":
                if not event_id:
                    self._distance_sequence += 1
                    sequence = self._distance_sequence
                    event_id = f"hc-sr04-{sequence}"
                elif event_id in self._ids:
                    return "duplicate"
                else:
                    sequence = int(payload.get("sequence") or self._distance_sequence + 1)
                    self._distance_sequence = max(self._distance_sequence, sequence)
                try:
                    centimeters = payload.get("distance_cm")
                    reading = DistanceReading.model_validate(
                        {
                            **payload,
                            "event_id": event_id,
                            "sequence": sequence,
                            "distance_cm": None if centimeters is None else float(centimeters),
                            "timestamp": received_at,
                            "received_at": received_at,
                            "port": port,
                            "source": "REAL_HARDWARE",
                            "sensor_id": payload.get("sensor_id") or "hc-sr04",
                            "valid": centimeters is not None,
                        }
                    )
                except (ValidationError, TypeError, ValueError):
                    return "invalid"
                self._ids.add(event_id)
                self.distances.append(reading)
                self.distances[:] = self.distances[-120:]
                return "distance"
            if event_id in self._ids:
                return "duplicate"
            if event_type not in {"boot_button", "manual_hardware_test"}:
                return "ignored"
            try:
                event = HardwareEvent.model_validate(
                    {
                        **payload,
                        "label": "MANUAL_HARDWARE_TEST",
                        "received_at": received_at,
                        "port": port,
                    }
                )
            except ValidationError:
                return "invalid"
            self._ids.add(event_id)
            self.events.append(event)
            self.events[:] = self.events[-200:]
            return "event"


class SerialBridge:
    def __init__(self, log: EventLog, on_change: Callable[[], None] | None = None) -> None:
        self.log = log
        self._on_change = on_change or (lambda: None)
        self._lock = threading.Lock()
        self.state = "DISCONNECTED"
        self.port: str | None = None
        self.error: str | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._serial: LinePort | None = None
        self.ultrasonic_enabled = True
        self.baud = 115200

    def snapshot(self) -> dict:
        with self._lock:
            distances = [reading.model_dump() for reading in self.log.distances]
            bench = [sample.model_dump() for sample in self.log.bench]
            return {
                "state": self.state,
                "link_status": _link_status(self.state, distances),
                "bench_status": _bench_status(self.state, bench),
                "port": self.port,
                "baud": self.baud,
                "error": self.error,
                "event_count": len(self.log.events),
                "distance_count": len(distances),
                "bench_count": len(bench),
                "ultrasonic_enabled": True,
                "events": [event.model_dump() for event in self.log.events],
                "distances": distances,
                "bench": bench,
                "notes": list(self.log.ignored_notes),
            }

    def set_ultrasonic_enabled(self, enabled: bool) -> None:
        with self._lock:
            self.ultrasonic_enabled = enabled
        self._on_change()

    def connect(self, port_name: str, opener: Callable[[str], LinePort] | None = None, baud: int = 115200) -> None:
        if baud not in ALLOWED_BAUD:
            raise ValueError(f"baud must be one of {', '.join(str(item) for item in ALLOWED_BAUD)}")
        self.disconnect()
        self.baud = baud
        open_port = opener or (lambda name: _open_serial(name, baud))
        try:
            serial_port = open_port(port_name)
        except Exception as exc:
            message = str(exc)
            if "Access is denied" in message or "PermissionError" in message:
                message = f"{port_name} is in use. Close the Arduino Serial Monitor, then connect again."
            with self._lock:
                self.state = "DISCONNECTED"
                self.port = None
                self.error = message
            self._on_change()
            raise RuntimeError(message) from exc
        with self._lock:
            self._serial = serial_port
            self.port = port_name
            self.state = "CONNECTED"
            self.error = None
            self._stop.clear()
            self._thread = threading.Thread(target=self._read_loop, name="esp32-serial", daemon=True)
            self._thread.start()
        self._on_change()

    def disconnect(self, reason: str | None = None) -> None:
        with self._lock:
            self._stop.set()
            serial_port = self._serial
            self._serial = None
            thread = self._thread
            self._thread = None
            self.state = "DISCONNECTED"
            self.port = None
            if reason:
                self.error = reason
        if serial_port is not None:
            try:
                serial_port.close()
            except Exception:
                pass
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.5)
        self._on_change()

    def _read_loop(self) -> None:
        while not self._stop.is_set():
            serial_port = self._serial
            port_name = self.port
            if serial_port is None or port_name is None:
                self.disconnect("serial reader stopped")
                return
            try:
                raw = serial_port.readline()
            except Exception:
                self.disconnect("serial port closed")
                return
            if self._stop.is_set():
                return
            if not raw:
                if not _port_present(port_name):
                    self.disconnect("serial port removed")
                    return
                continue
            try:
                text = raw.decode("utf-8", errors="replace")
            except Exception:
                continue
            parsed = parse_serial_line(text)
            if parsed.event is None:
                continue
            from datetime import datetime, timezone

            kind = self.log.add(
                parsed.event,
                port=port_name,
                received_at=datetime.now(timezone.utc).isoformat(),
                ultrasonic_enabled=self.ultrasonic_enabled,
            )
            if kind in {"event", "distance", "duplicate", "ignored", "bench"}:
                self._on_change()

    def inject_line(self, line: str, *, port: str = "TEST") -> str:
        """Parse one line as if it arrived on an already connected port. Used by tests."""
        parsed = parse_serial_line(line)
        if parsed.event is None:
            return parsed.error or "ignored"
        from datetime import datetime, timezone

        with self._lock:
            self.state = "CONNECTED"
            self.port = port
        return self.log.add(
            parsed.event,
            port=port,
            received_at=datetime.now(timezone.utc).isoformat(),
            ultrasonic_enabled=self.ultrasonic_enabled,
        )


def list_ports() -> list[SerialPortInfo]:
    try:
        from serial.tools import list_ports as serial_list_ports
    except ImportError:
        return []
    found: list[SerialPortInfo] = []
    for port in serial_list_ports.comports():
        found.append(SerialPortInfo(device=port.device, description=port.description or "", hwid=port.hwid or ""))
    return found


def _open_serial(port_name: str, baud: int = 115200) -> LinePort:
    import serial

    return serial.Serial(port_name, baudrate=baud, timeout=0.3)


def _link_status(state: str, samples: list[dict], stale_after: float = STALE_AFTER_S) -> str:
    if state != "CONNECTED":
        return "DISCONNECTED"
    if not samples:
        return "STALE"
    stamp = samples[-1].get("timestamp") or ""
    try:
        parsed = datetime.fromisoformat(str(stamp))
    except ValueError:
        return "STALE"
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if (datetime.now(timezone.utc) - parsed).total_seconds() > stale_after:
        return "STALE"
    return "CONNECTED"


def _bench_status(state: str, samples: list[dict]) -> str:
    if state != "CONNECTED":
        return "DISCONNECTED"
    if not samples:
        return "WAITING"
    return _link_status(state, samples, stale_after=1.5)


def _port_present(port_name: str) -> bool:
    if port_name == "TEST":
        return True
    return any(port.device == port_name for port in list_ports())


bridge = SerialBridge(EventLog())


def monotonic_ms() -> int:
    return int(time.monotonic() * 1000)
