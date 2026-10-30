"""Stop the sweep program and release both servo signals."""

import os
import signal
import time


def _kill_sweep() -> None:
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            raw = open("/proc/" + name + "/cmdline", "rb").read().replace(b"\x00", b" ").decode()
        except Exception:
            continue
        if "sweep.py" not in raw:
            continue
        if not raw.startswith("python"):
            continue
        os.kill(int(name), signal.SIGTERM)
        print("stopped", name, flush=True)


def _release() -> None:
    from gpiozero import AngularServo

    for pin in (18, 19):
        servo = AngularServo(
            pin,
            min_angle=0,
            max_angle=180,
            min_pulse_width=0.0005,
            max_pulse_width=0.0025,
            initial_angle=None,
        )
        servo.value = None
        servo.close()
        print("released", pin, flush=True)


if __name__ == "__main__":
    _kill_sweep()
    time.sleep(0.3)
    try:
        _release()
    except Exception as exc:
        print("release failed", exc, flush=True)
