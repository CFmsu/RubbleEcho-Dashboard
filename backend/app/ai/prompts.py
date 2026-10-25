import json

SYSTEM_PROMPT = """You are an advisory reviewer for a sand-table sensor trial.
Return one JSON object and no markdown.
Use only the evidence in the user message.
Do not invent sensors, rates, angles, coordinates, or a living person.
Do not request motor voltage, PWM, or pin changes.
Every recommendation requires operator approval.
A numeric score is a model assessment, not a calibrated probability.
If the evidence is thin, say so in unknowns and set recommendation.type to needs_operator.
Allowed recommendation types: stop, rescan_at_point, capture, settle_and_listen, needs_operator.
If a search plan is included, choose rescan_at_point only for a point_id that is still on its path.
The plan is a grid order. It is not a motor command.
event_ids and evidence_event_ids must be JSON arrays of strings copied from the evidence event_id values.
score is a number from 0 to 1.
recommendation.requires_approval must be true.
recommendation.point_id must be one of the supplied point_ids, or null.
Keep hypotheses to one item and the summary to one sentence, so the JSON is finished.
"""


def build_messages(
    evidence: list[dict],
    point_ids: list[str],
    search_plan: dict | None = None,
) -> list[dict[str, str]]:
    payload = {
        "point_ids": point_ids,
        "evidence": evidence,
        "search_plan": _plan_brief(search_plan),
        "constraints": [
            "hidden source labels are not included",
            "radar through-sand vital signs are not validated",
            "do not output motor voltages",
            "a search path is a list of grid point ids, not a speed or a pin",
            "response_shape is a format sample. Do not copy evt_0001. Use event_id values from evidence",
        ],
        "response_shape": {
            "event_ids": ["evt_0001"],
            "hypotheses": [
                {
                    "label": "short_label",
                    "score": 0.4,
                    "evidence_event_ids": ["evt_0001"],
                    "limitations": ["what this evidence cannot prove"],
                }
            ],
            "summary": "One sentence that uses only the evidence.",
            "recommendation": {
                "type": "needs_operator",
                "point_id": None,
                "requires_approval": True,
            },
            "unknowns": ["one gap in the evidence"],
        },
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, sort_keys=True)},
    ]


def _plan_brief(search_plan: dict | None) -> dict | None:
    if not search_plan:
        return None
    return {
        "path": search_plan.get("path"),
        "look": search_plan.get("look"),
        "blocked": [
            cell["point_id"]
            for cell in search_plan.get("cells") or []
            if cell.get("state") == "blocked"
        ],
    }


PLAN_PROMPT = """You plan a sand-table search grid from a camera note and the known points.
Return one JSON object and no markdown.
Keys: boundary, path, look, summary.
boundary is a list of lines with x1_cm, y1_cm, x2_cm, y2_cm inside the table.
path is an ordered list of the supplied point ids and may not add ids.
look is forward, left, or right. That is a planned sensor facing, not a motor turn.
Do not include speed, voltage, pwm, pin, or motor_speed.
If photo.scene is present, it is the only description of the picture. Do not add obstacles it does not mention.
"""


SCENE_PROMPT = """You describe one camera frame from a sand-table search.
Return one JSON object and no markdown.
Keys: scene, obstacles, open_area.
scene is one sentence about what is visible.
obstacles is a list of short phrases. Use an empty list when no blocker is visible.
open_area is one sentence about the clear region, or "not visible".
Do not invent a person, a distance, an angle, or a motor command.
"""


def build_scene_messages(note: str, data_url: str) -> list[dict]:
    return [
        {"role": "system", "content": SCENE_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": note or "Describe only what is visible in this frame."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]


def build_plan_messages(photo: dict, point_ids: list[str]) -> list[dict[str, str]]:
    payload = {"photo": photo, "point_ids": point_ids}
    return [
        {"role": "system", "content": PLAN_PROMPT},
        {"role": "user", "content": json.dumps(payload, sort_keys=True)},
    ]
