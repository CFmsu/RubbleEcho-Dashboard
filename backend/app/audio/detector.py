import math

from dataclasses import asdict, dataclass

from app.services.feature_extraction import HOP_MS, classify_window, dbfs

LABELS = {
    "knock": "POSSIBLE_KNOCK",
    "scratch/scrape": "POSSIBLE_SCRATCH",
    "silence": "BACKGROUND",
    "ambient": "BACKGROUND",
    "unknown": "UNKNOWN",
}


def detect_event(samples: list[float], sample_rate: float) -> dict:
    """Local detector. It is not a trained model and it does not hear a heartbeat."""
    raw = classify_window(samples, sample_rate, context={"source_mode": "analysis"})
    rms = raw.get("rms_dbfs")
    peak = raw.get("peak_dbfs")
    centroid = raw.get("centroid_hz")
    features = {
        "rms_dbfs": rms,
        "peak_dbfs": peak,
        "centroid_hz": centroid,
        "crest": _crest(samples),
        "zero_crossing_rate": _zero_crossing_rate(samples),
    }
    return {
        "event": LABELS.get(raw["class"], "UNKNOWN"),
        "training_status": "NOT_TRAINED",
        "score": None,
        "features": features,
        "finite": _finite(features),
        "heartbeat": "UNVERIFIED",
        "limitations": raw.get("limitations", []),
        "unit_note": "dBFS is digital full scale, not sound pressure.",
    }


def _crest(samples: list[float]) -> float | None:
    if not samples:
        return None
    peak = max(abs(sample) for sample in samples)
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    if rms <= 1e-12:
        return None
    return peak / rms


def _zero_crossing_rate(samples: list[float]) -> float | None:
    if len(samples) < 2:
        return None
    crossings = 0
    for left, right in zip(samples, samples[1:]):
        if left == 0 or right == 0:
            continue
        if (left > 0) != (right > 0):
            crossings += 1
    return crossings / (len(samples) - 1)


@dataclass
class AcousticCalibration:
    """Shape thresholds. Fitted on the synthetic array set, not on rubble recordings."""

    rise_ratio: float = 8.0
    crest_min: float = 6.0
    decay_fraction: float = 0.35
    knock_max_hops: int = 12
    flatness_min: float = 0.25
    band_fraction_min: float = 0.55
    scratch_rms_ratio: float = 3.0
    scratch_min_hops: int = 125
    scratch_max_hops: int = 500
    ioi_cv_max: float = 0.15
    floor_hops: int = 40
    refractory_hops: int = 8
    training_status: str = "SHAPE_RULES"
    hardware_calibrated: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "AcousticCalibration":
        known = {key: payload[key] for key in cls.__dataclass_fields__ if key in payload}
        return cls(**known)


class EventTracker:
    """Hop consumer. Knock duration is counted in 4 ms steps. No piezo input."""

    def __init__(self, calibration: AcousticCalibration | None = None, source_mode: str = "dummy") -> None:
        self.cal = calibration or AcousticCalibration()
        self.source_mode = source_mode
        self._hist: list[float] = []
        self._prev_rms = 0.0
        self._prev2_rms = 0.0
        self._prev_crest = 0.0
        self.knock: dict | None = None
        self.scratch: dict | None = None
        self.scratch_dead = False
        self.onsets: list[int] = []
        self.refractory_until = -1
        self.last_hop = -1

    def feed(self, features: dict) -> list[dict]:
        hop = int(features["hop"])
        self.last_hop = hop
        rms = float(features["rms"])
        crest = float(features["crest"])
        floor = self._floor()
        events: list[dict] = []
        if floor is None:
            self._hist.append(rms)
            self._shift_prev(rms, crest)
            return events

        rise = rms / max(floor, 1e-8)
        self._track_knock(features, hop, rms, crest, rise, floor, events)
        self._track_scratch(features, hop, rms, crest, rise, floor, events)
        loud = rms > floor * 2.5 or self.knock is not None or (self.scratch is not None and not self.scratch_dead)
        if not loud:
            self._hist.append(rms)
            if len(self._hist) > 250:
                self._hist = self._hist[-250:]
        self._shift_prev(rms, crest)
        return events

    def _shift_prev(self, rms: float, crest: float) -> None:
        self._prev2_rms = self._prev_rms
        self._prev_rms = rms
        self._prev_crest = crest

    def finish(self) -> list[dict]:
        """Close a scratch that was still sounding when a finite clip ended."""
        if self.scratch is None or self.scratch_dead or self.last_hop < 0:
            return []
        elapsed = self.last_hop - int(self.scratch["start"]) + 1
        self.scratch_dead = True
        if self.cal.scratch_min_hops <= elapsed <= self.cal.scratch_max_hops:
            floor = self._floor() or 0.0
            return [self._scratch_event(elapsed, floor)]
        return []

    def _floor(self) -> float | None:
        if len(self._hist) < self.cal.floor_hops:
            return None
        import numpy as np

        values = np.asarray(self._hist, dtype=np.float64)
        med = float(np.median(values))
        quiet = values[values <= max(med * 2.0, 1e-8)]
        if quiet.size < self.cal.floor_hops // 2:
            quiet = values
        return float(np.median(quiet))

    def _track_knock(
        self,
        features: dict,
        hop: int,
        rms: float,
        crest: float,
        rise: float,
        floor: float,
        events: list[dict],
    ) -> None:
        if self.knock is None:
            jumped = self._prev_rms > 0 and (
                rms >= self._prev_rms * 3.0 or (self._prev2_rms > 0 and rms >= self._prev2_rms * 3.0)
            )
            crest_ok = crest >= self.cal.crest_min or self._prev_crest >= self.cal.crest_min
            if hop >= self.refractory_until and jumped and rise >= self.cal.rise_ratio and crest_ok:
                self.knock = {
                    "start": hop,
                    "peak_rms": rms,
                    "peak": float(features["peak"]),
                    "energies": [rms],
                    "frame": features.get("frame"),
                    "channel": int(features["channel"]),
                }
            return

        age = hop - int(self.knock["start"])
        self.knock["energies"].append(rms)
        if rms >= self.knock["peak_rms"]:
            self.knock["peak_rms"] = rms
            self.knock["peak"] = float(features["peak"])
            self.knock["frame"] = features.get("frame")
            self.knock["channel"] = int(features["channel"])
        fallen = rms <= max(floor * 2.0, self.knock["peak_rms"] * self.cal.decay_fraction)
        if fallen and 2 <= age <= self.cal.knock_max_hops and _decaying(self.knock["energies"]):
            events.append(self._knock_event(hop, age))
            self.knock = None
            self.refractory_until = hop + self.cal.refractory_hops
        elif age > self.cal.knock_max_hops:
            self.knock = None

    def _track_scratch(
        self,
        features: dict,
        hop: int,
        rms: float,
        crest: float,
        rise: float,
        floor: float,
        events: list[dict],
    ) -> None:
        # In-band flatness is high for friction noise and low for a tone or motor whine.
        condition = (
            self.knock is None
            and float(features["flatness"]) >= self.cal.flatness_min
            and float(features["band_fraction"]) >= self.cal.band_fraction_min
            and rise >= self.cal.scratch_rms_ratio
            and crest < self.cal.crest_min
        )
        if self.scratch is None:
            if condition:
                self.scratch = {
                    "start": hop,
                    "rms": rms,
                    "peak": float(features["peak"]),
                    "flatness": float(features["flatness"]),
                    "band_fraction": float(features["band_fraction"]),
                    "spectral_flux": float(features["spectral_flux"]),
                    "channel": int(features["channel"]),
                }
                self.scratch_dead = False
            return
        if self.scratch_dead:
            if not condition:
                self.scratch = None
                self.scratch_dead = False
            return
        elapsed = hop - int(self.scratch["start"])
        if condition:
            if rms >= self.scratch["rms"]:
                self.scratch["rms"] = rms
                self.scratch["peak"] = float(features["peak"])
                self.scratch["channel"] = int(features["channel"])
            self.scratch["flatness"] = float(features["flatness"])
            self.scratch["band_fraction"] = float(features["band_fraction"])
            self.scratch["spectral_flux"] = float(features["spectral_flux"])
            if elapsed > self.cal.scratch_max_hops:
                self.scratch_dead = True
            return
        if self.cal.scratch_min_hops <= elapsed <= self.cal.scratch_max_hops:
            events.append(self._scratch_event(elapsed, floor))
        self.scratch = None

    def _knock_event(self, hop: int, age: int) -> dict:
        assert self.knock is not None
        self.onsets.append(int(self.knock["start"]))
        label = "periodic_tapping" if self._periodic() else "knock"
        peak = float(self.knock["peak_rms"])
        return _live_event(
            label,
            peak,
            float(self.knock["peak"]),
            age * HOP_MS,
            int(self.knock["channel"]),
            self.knock.get("frame"),
            self.source_mode,
            self.cal,
            extra={"inter_onset_hops": list(self.onsets[-3:]), "rise_hops": age},
        )

    def _scratch_event(self, elapsed: int, floor: float) -> dict:
        assert self.scratch is not None
        return _live_event(
            "scratch/scrape",
            float(self.scratch["rms"]),
            float(self.scratch["peak"]),
            elapsed * HOP_MS,
            int(self.scratch["channel"]),
            None,
            self.source_mode,
            self.cal,
            extra={
                "flatness": round(float(self.scratch["flatness"]), 3),
                "band_fraction": round(float(self.scratch["band_fraction"]), 3),
                "spectral_flux": round(float(self.scratch["spectral_flux"]), 6),
                "floor_rms": floor,
            },
        )

    def _periodic(self) -> bool:
        if len(self.onsets) < 3:
            return False
        gaps = [self.onsets[-2] - self.onsets[-3], self.onsets[-1] - self.onsets[-2]]
        if min(gaps) <= 0:
            return False
        # cv of two intervals: |d1-d2| / (d1+d2). Equal spacing is 0.
        cv = abs(gaps[0] - gaps[1]) / (gaps[0] + gaps[1])
        return cv <= self.cal.ioi_cv_max


def _decaying(energies: list[float]) -> bool:
    import numpy as np

    if len(energies) < 3:
        return False
    peak_at = int(np.argmax(energies))
    tail = energies[peak_at:]
    if len(tail) < 2:
        return False
    start = max(float(tail[0]), 1e-8)
    end = max(float(tail[-1]), 1e-8)
    slope = (np.log(end) - np.log(start)) / (len(tail) - 1)
    return float(slope) < 0.0


def _live_event(
    label: str,
    rms: float,
    peak: float,
    duration_ms: float,
    channel: int,
    frame: object,
    source_mode: str,
    calibration: AcousticCalibration,
    extra: dict,
) -> dict:
    return {
        "class": label,
        "rms_dbfs": dbfs(rms),
        "peak_dbfs": dbfs(peak),
        "model_score": None,
        "score_semantics": "shape_rule_on_synthetic_calibration",
        "origin_unknown": True,
        "site_id": None,
        "source_mode": source_mode,
        "duration_ms": round(duration_ms, 1),
        "onset": label != "scratch/scrape",
        "channel": channel,
        "frame": frame,
        "centroid_hz": None,
        "training_status": calibration.training_status,
        "hardware_calibrated": calibration.hardware_calibrated,
        "channel_note": "4 raw mic channels. Processed mix and loopback are not used. No piezo in this path.",
        "limitations": [
            "thresholds_fit_on_synthetic_array_clips",
            "no_piezo_veto",
            "tdoa_is_an_array_delay_not_a_buried_bearing",
            "requires_raw_6_channel_firmware",
        ],
        "detail": extra,
    }


def _finite(features: dict) -> bool:
    for value in features.values():
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if not math.isfinite(value):
            return False
    return True
