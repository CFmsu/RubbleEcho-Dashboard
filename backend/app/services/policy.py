from app.config.geometry import point_in_traversable
from app.config.settings import (
    MAX_MOVE_CM,
    MAX_TURN_DEG,
    ULTRASONIC_CAUTION_CM,
    ULTRASONIC_STOP_CM,
)
from app.drivers.encoders import ALLOWED_COMMANDS

HARD_STOP_REASONS = {
    "missing_echo",
    "obstacle_inside_stop_margin",
    "out_of_bounds",
    "stale_pose",
    "invalid_pose",
    "encoder_timeout",
    "operator_link_lost",
    "duplicate_command",
    "command_not_allowed",
}


def assess_motion(context: dict) -> dict:
    reasons: list[str] = []
    distance = context.get("distance_cm")
    if context.get("echo_timeout") or distance is None:
        reasons.append("missing_echo")
    else:
        stop_margin = context.get("stop_margin_cm", ULTRASONIC_STOP_CM)
        caution_margin = context.get("caution_margin_cm", ULTRASONIC_CAUTION_CM)
        if distance < stop_margin:
            reasons.append("obstacle_inside_stop_margin")
        elif distance < caution_margin:
            reasons.append("inside_caution_margin")

    if not context.get("pose_valid"):
        reasons.append("invalid_pose")
    elif context.get("pose_age_ms", 10**9) > context.get("pose_timeout_ms", 1000):
        reasons.append("stale_pose")

    if context.get("require_heading") and context.get("heading_deg") is None:
        reasons.append("heading_unknown")

    if context.get("target_x_cm") is not None:
        if not point_in_traversable(context["target_x_cm"], context["target_y_cm"]):
            reasons.append("out_of_bounds")

    if context.get("encoder_fresh") is not True:
        reasons.append("encoder_timeout")

    if context.get("mode") == "live" and not context.get("operator_link"):
        reasons.append("operator_link_lost")

    hard = [reason for reason in reasons if reason in HARD_STOP_REASONS]
    return {
        "accepted": not reasons,
        "reasons": reasons,
        "hard_stop": bool(hard),
        "transmitted": False,
        "execute_hardware": False,
    }


def vet_command(command: dict, context: dict, seen_ids: set[str]) -> dict:
    command_type = command.get("type")
    command_id = command.get("command_id")
    if command_type not in ALLOWED_COMMANDS:
        return _decision(False, ["command_not_allowed"], True, disarm=True)
    if not command_id or command_id in seen_ids:
        return _decision(False, ["duplicate_command"], True, disarm=True)
    if command_type == "stop":
        return _decision(True, [], False, safety="STOP")
    if command_type == "move_cm":
        distance = command.get("distance_cm")
        if (
            isinstance(distance, bool)
            or not isinstance(distance, (int, float))
            or distance <= 0
            or distance > MAX_MOVE_CM
        ):
            return _decision(False, ["move_out_of_range"], False)
        return assess_motion({**context, "require_heading": True})
    if command_type == "turn_deg":
        angle = command.get("turn_deg")
        if (
            isinstance(angle, bool)
            or not isinstance(angle, (int, float))
            or abs(angle) > MAX_TURN_DEG
        ):
            return _decision(False, ["turn_out_of_range"], False)
        if context.get("encoder_fresh") is not True:
            return _decision(False, ["encoder_timeout"], True, disarm=True)
        return _decision(False, ["NEEDS_HARDWARE_VERIFICATION"], False)
    if command_type in {"rescan", "capture"}:
        return _decision(True, ["NEEDS_HARDWARE_VERIFICATION"], False)
    return _decision(False, ["handled_by_solenoid"], False)


def on_link_lost(mode: str) -> dict:
    if mode == "live":
        return {
            "safety": "ESTOP",
            "phase": "ESTOP",
            "disarm": True,
            "reason": "operator_link_lost",
        }
    return {"safety": None, "phase": None, "disarm": False, "reason": "link_lost_ignored_not_live"}


def on_cloud_failure(kind: str) -> dict:
    return {
        "safety": "STOP",
        "phase": "FAULT",
        "disarm": True,
        "reason": kind,
        "execute_hardware": False,
    }


def _decision(
    accepted: bool,
    reasons: list[str],
    hard_stop: bool,
    disarm: bool = False,
    safety: str | None = None,
) -> dict:
    return {
        "accepted": accepted,
        "reasons": reasons,
        "hard_stop": hard_stop,
        "transmitted": False,
        "execute_hardware": False,
        "disarm": disarm,
        "safety": safety,
    }
