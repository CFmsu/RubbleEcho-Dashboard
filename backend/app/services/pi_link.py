"""Commands for the Uno when its USB cable is plugged into the Pi, not this laptop."""

import threading

_lock = threading.Lock()
_commands: list[str] = []


_operator: list[dict] = []


def reset() -> None:
    with _lock:
        _commands.clear()
        _operator.clear()


def enqueue(command: str) -> None:
    with _lock:
        if len(command) == 1 and command in "AFBLRS":
            _commands[:] = [item for item in _commands if not (len(item) == 1 and item in "AFBLRS")]
        elif len(command) == 1 and command in "0123456789":
            _commands[:] = [item for item in _commands if not (len(item) == 1 and item in "0123456789")]
        _commands.append(command)


def take_commands() -> list[str]:
    with _lock:
        commands = list(_commands)
        _commands.clear()
        return commands


def enqueue_operator(kind: str, body: dict | None = None) -> None:
    """Servo and capture jobs. These stay off the Uno letter queue."""
    item = {"kind": kind}
    if body:
        item.update(body)
    with _lock:
        if kind == "servo":
            horn = item.get("horn")
            _operator[:] = [
                job for job in _operator if not (job.get("kind") == "servo" and job.get("horn") == horn)
            ]
        elif kind in {"deploy", "collect"}:
            _operator[:] = [job for job in _operator if job.get("kind") != kind]
        _operator.append(item)


def take_operator() -> list[dict]:
    with _lock:
        jobs = list(_operator)
        _operator.clear()
        return jobs


def accept_lines(lines: list[str]) -> int:
    from app.services.rover_track import apply_rover_line

    applied = 0
    for line in lines:
        if isinstance(line, str) and apply_rover_line(line):
            applied += 1
    return applied
