import math


def dbfs(amplitude: float) -> float | None:
    if amplitude <= 1e-12:
        return None
    return 20.0 * math.log10(amplitude)


def spectral_centroid_hz(samples: list[float], sample_rate: float) -> float | None:
    count = min(len(samples), 64)
    if count < 8 or sample_rate <= 0:
        return None
    window = samples[:count]
    weighted = 0.0
    total = 0.0
    half = count // 2
    for bin_index in range(1, half):
        real = 0.0
        imag = 0.0
        for index, sample in enumerate(window):
            angle = -2.0 * math.pi * bin_index * index / count
            real += sample * math.cos(angle)
            imag += sample * math.sin(angle)
        magnitude = math.hypot(real, imag)
        frequency = bin_index * sample_rate / count
        weighted += frequency * magnitude
        total += magnitude
    if total <= 1e-9:
        return None
    return weighted / total


def envelope_dbfs(samples: list[float], buckets: int = 40) -> list[float]:
    """Digital envelope for drawing. Exact zeros use a -80 dBFS display floor."""
    if not samples:
        return []
    size = max(1, math.ceil(len(samples) / buckets))
    envelope: list[float] = []
    for start in range(0, len(samples), size):
        chunk = samples[start : start + size]
        rms = math.sqrt(sum(value * value for value in chunk) / len(chunk))
        level = dbfs(rms)
        envelope.append(-80.0 if level is None else level)
    return envelope


def classify_window(
    samples: list[float],
    sample_rate: float,
    captured_at_utc: str | None = None,
    context: dict | None = None,
) -> dict:
    """Threshold classifier for normalized fixture or captured digital audio.

    Scores are uncalibrated. The classifier does not emit a speech class and does
    not claim that a sound came from under the sand.
    """
    context = context or {}
    limitations = [
        "uncalibrated_thresholds",
        "origin_unknown",
        "not_calibrated_to_sound_pressure",
    ]
    if context.get("motors_running"):
        limitations.append("motors_running_contamination_possible")
    if context.get("solenoid_commanded"):
        limitations.append(
            "cannot_separate_striker_self_noise_without_reference_piezo"
        )

    if not samples or sample_rate <= 0:
        return _event(
            "unknown",
            captured_at_utc,
            0.0,
            None,
            None,
            None,
            False,
            None,
            context,
            limitations + ["no_samples"],
        )

    peak = max(abs(sample) for sample in samples)
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    high_fraction = sum(1 for sample in samples if abs(sample) >= 0.1) / len(samples)
    duration_ms = 1000.0 * len(samples) / sample_rate
    centroid = spectral_centroid_hz(samples, sample_rate)

    label = "unknown"
    onset = False
    if rms < 0.01 and peak < 0.05:
        label = "silence"
    elif peak >= 0.45 and high_fraction < 0.2:
        label = "knock"
        onset = True
    elif peak >= 0.15 and high_fraction >= 0.5:
        label = "scratch/scrape"
        onset = True
    elif rms < 0.05:
        label = "ambient"
    else:
        limitations.append("speech_classifier_not_calibrated")

    raw_score = None
    if label in {"knock", "scratch/scrape"}:
        raw_score = round(min(1.0, peak), 3)

    return _event(
        label,
        captured_at_utc,
        duration_ms,
        dbfs(rms),
        dbfs(peak),
        centroid,
        onset,
        raw_score,
        context,
        limitations,
    )


def _event(
    label: str,
    captured_at_utc: str | None,
    duration_ms: float,
    rms_level: float | None,
    peak_level: float | None,
    centroid: float | None,
    onset: bool,
    raw_score: float | None,
    context: dict,
    limitations: list[str],
) -> dict:
    return {
        "class": label,
        "start_utc": captured_at_utc,
        "duration_ms": duration_ms,
        "rms_dbfs": rms_level,
        "peak_dbfs": peak_level,
        "centroid_hz": centroid,
        "onset": onset,
        "model_label": None,
        "model_score": raw_score,
        "score_semantics": "uncalibrated_raw_score" if raw_score is not None else "not_scored",
        "raw_clip_id": None,
        "origin_unknown": True,
        "site_id": context.get("site_id"),
        "limitations": limitations,
        "source_mode": context.get("source_mode", "unavailable"),
        "possible_self_noise": bool(
            context.get("solenoid_commanded") and label == "knock"
        ),
        "unit_note": "dBFS is digital full scale, not dB SPL",
    }


# Live path. 16 kHz, 256-point Hann window, hop 64 samples = 4.0 ms.
# Bin width is 16000/256 = 62.5 Hz. Scratch energy uses bins from 1 kHz to 4 kHz.
RATE_HZ = 16000
WINDOW_SAMPLES = 256
HOP_SAMPLES = 64
HOP_MS = 1000.0 * HOP_SAMPLES / RATE_HZ
BANDPASS_HZ = (50.0, 4000.0)
SCRATCH_BAND_HZ = (1000.0, 4000.0)


class StreamingBandpass:
    """50–4000 Hz Butterworth applied per channel with state carried across blocks.

    Order 2 keeps the impulse response short enough that a tap under 50 ms is not
    smeared by the filter. `zi` is updated on every block. Restarting from zeros
    at each block boundary rings and looks like a false onset.
    """

    def __init__(self, channels: int = 4, sample_rate: float = RATE_HZ, order: int = 2) -> None:
        import numpy as np
        from scipy.signal import butter

        nyquist = sample_rate / 2.0
        low, high = BANDPASS_HZ
        self.sos = butter(order, [low / nyquist, high / nyquist], btype="bandpass", output="sos")
        self.channels = channels
        self._np = np
        self._zi = np.zeros((channels, self.sos.shape[0], 2), dtype=np.float64)
        self._primed = False

    def process(self, block: object) -> object:
        import numpy as np
        from scipy.signal import sosfilt, sosfilt_zi

        data = np.asarray(block, dtype=np.float64)
        if data.ndim != 2 or data.shape[1] != self.channels or data.shape[0] == 0:
            raise ValueError("bandpass expects shape (frames, 4)")
        if not self._primed:
            seed = sosfilt_zi(self.sos)
            for channel in range(self.channels):
                self._zi[channel] = seed * float(data[0, channel])
            self._primed = True
        out = np.empty_like(data)
        for channel in range(self.channels):
            out[:, channel], self._zi[channel] = sosfilt(self.sos, data[:, channel], zi=self._zi[channel])
        return out


def spectral_flatness(magnitudes: object) -> float:
    """Geometric mean / arithmetic mean of bin magnitudes. Near 0 is tonal. Near 1 is noise-like."""
    import numpy as np

    mag = np.asarray(magnitudes, dtype=np.float64)
    mag = mag[np.isfinite(mag)]
    if mag.size < 4:
        return 0.0
    geometric = float(np.exp(np.mean(np.log(mag + 1e-12))))
    arithmetic = float(np.mean(mag))
    if arithmetic <= 1e-12:
        return 0.0
    return geometric / arithmetic


class HopAnalyzer:
    """Fine hop features. The 256-sample window slides by 64 samples."""

    def __init__(self, channels: int = 4, sample_rate: float = RATE_HZ) -> None:
        import numpy as np

        self.channels = channels
        self.sample_rate = sample_rate
        self.window = WINDOW_SAMPLES
        self.hop = HOP_SAMPLES
        self._buf = np.zeros((0, channels), dtype=np.float64)
        self.hop_index = 0
        self._window_fn = np.hanning(self.window)
        self._freqs = np.fft.rfftfreq(self.window, d=1.0 / sample_rate)
        self._scratch_bins = (self._freqs >= SCRATCH_BAND_HZ[0]) & (self._freqs <= SCRATCH_BAND_HZ[1])
        self._prev_mag: object | None = None

    def push(self, block: object) -> list[dict]:
        import numpy as np

        data = np.asarray(block, dtype=np.float64)
        if data.ndim != 2 or data.shape[1] != self.channels:
            raise ValueError("hop analyzer expects shape (frames, 4)")
        self._buf = data if self._buf.size == 0 else np.vstack((self._buf, data))
        features: list[dict] = []
        while self._buf.shape[0] >= self.window:
            features.append(self._frame(self._buf[: self.window]))
            self._buf = self._buf[self.hop :]
            self.hop_index += 1
        return features

    def _frame(self, frame: object) -> dict:
        import numpy as np

        samples = np.asarray(frame, dtype=np.float64)
        weighted = samples * self._window_fn[:, None]
        spectrum = np.fft.rfft(weighted, axis=0)
        magnitude = np.abs(spectrum)
        rms = np.sqrt(np.mean(samples * samples, axis=0))
        peak = np.max(np.abs(samples), axis=0)
        crest = peak / np.maximum(rms, 1e-12)
        loudest = int(np.argmax(rms))
        loud_mag = magnitude[:, loudest]
        scratch = loud_mag[self._scratch_bins]
        usable = loud_mag[1:]
        scratch_energy = float(np.sum(scratch * scratch))
        total_energy = float(np.sum(usable * usable)) + 1e-18
        if self._prev_mag is None:
            flux = 0.0
        else:
            delta = loud_mag - self._prev_mag
            flux = float(np.sqrt(np.mean(delta * delta)))
        self._prev_mag = loud_mag.copy()
        return {
            "hop": self.hop_index,
            "rms": float(rms[loudest]),
            "peak": float(peak[loudest]),
            "crest": float(crest[loudest]),
            "channel": loudest,
            "band_fraction": scratch_energy / total_energy,
            "flatness": spectral_flatness(scratch),
            "spectral_flux": flux,
            "frame": samples.copy(),
        }
