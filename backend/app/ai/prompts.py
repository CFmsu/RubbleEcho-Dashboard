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
"""


def build_messages(evidence: list[dict], point_ids: list[str]) -> list[dict[str, str]]:
    payload = {
        "point_ids": point_ids,
        "evidence": evidence,
        "constraints": [
            "hidden source labels are not included",
            "radar through-sand vital signs are not validated",
            "do not output motor voltages",
        ],
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, sort_keys=True)},
    ]
