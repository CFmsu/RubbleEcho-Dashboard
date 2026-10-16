"""Named simulation scenarios. These are inspired by disaster-response conditions, not reconstructions of individual events or victims."""

from __future__ import annotations

from models.mission import SimulationConfig


SCENARIOS: dict[str, dict] = {
    "earthquake_rubble": {
        "label": "Earthquake Rubble",
        "summary": "Simulation scenario inspired by earthquake debris fields.",
        "width": 12,
        "height": 12,
        "survivor_x": 8.4,
        "survivor_y": 5.6,
        "noise_level": 0.2,
        "response_probability": 0.78,
        "sensor_reliability": 0.88,
        "seed": 11,
        "surface": "concrete",
    },
    "flash_flood": {
        "label": "Flash Flood Debris",
        "summary": "Simulation scenario inspired by flash-flood debris and mud.",
        "width": 12,
        "height": 10,
        "survivor_x": 6.4,
        "survivor_y": 7.1,
        "noise_level": 0.24,
        "response_probability": 0.7,
        "sensor_reliability": 0.84,
        "seed": 23,
        "surface": "mud",
    },
    "landslide": {
        "label": "Landslide",
        "summary": "Simulation scenario inspired by landslide debris.",
        "width": 14,
        "height": 10,
        "survivor_x": 9.2,
        "survivor_y": 4.4,
        "noise_level": 0.22,
        "response_probability": 0.74,
        "sensor_reliability": 0.86,
        "seed": 31,
        "surface": "mixed",
    },
    "structural_collapse": {
        "label": "Structural Collapse",
        "summary": "Generic collapsed-structure search sector.",
        "width": 12,
        "height": 12,
        "survivor_x": 7.2,
        "survivor_y": 6.4,
        "noise_level": 0.16,
        "response_probability": 0.84,
        "sensor_reliability": 0.9,
        "seed": 42,
        "surface": "concrete",
    },
    "turkiye_earthquake": {
        "label": "Türkiye Earthquake Rubble",
        "summary": "Simulation scenario inspired by 2023 Türkiye earthquake rubble conditions. Not a reconstruction of any individual site or person.",
        "width": 12,
        "height": 12,
        "survivor_x": 8.1,
        "survivor_y": 7.4,
        "noise_level": 0.2,
        "response_probability": 0.8,
        "sensor_reliability": 0.88,
        "seed": 2023,
        "surface": "concrete",
    },
    "nepal_earthquake": {
        "label": "Nepal Earthquake Debris",
        "summary": "Simulation scenario inspired by Nepal earthquake debris conditions. Not a reconstruction of any individual site or person.",
        "width": 12,
        "height": 12,
        "survivor_x": 5.8,
        "survivor_y": 8.2,
        "noise_level": 0.21,
        "response_probability": 0.76,
        "sensor_reliability": 0.86,
        "seed": 2015,
        "surface": "masonry",
    },
    "nepal_flood": {
        "label": "Nepal Flash Flood Debris",
        "summary": "Simulation scenario inspired by Nepal flash-flood debris conditions. Not a reconstruction of any individual site or person.",
        "width": 12,
        "height": 10,
        "survivor_x": 7.6,
        "survivor_y": 6.8,
        "noise_level": 0.25,
        "response_probability": 0.72,
        "sensor_reliability": 0.84,
        "seed": 77,
        "surface": "mud",
    },
}


def scenario_label(scenario_id: str) -> str:
    item = SCENARIOS.get(scenario_id)
    if not item:
        return scenario_id.replace("_", " ").title()
    return item["label"]


def config_from_scenario(scenario_id: str, **overrides) -> SimulationConfig:
    base = SCENARIOS.get(scenario_id, SCENARIOS["structural_collapse"])
    data = {
        "width": base["width"],
        "height": base["height"],
        "survivor_x": base["survivor_x"],
        "survivor_y": base["survivor_y"],
        "noise_level": base["noise_level"],
        "response_probability": base["response_probability"],
        "sensor_reliability": base["sensor_reliability"],
        "seed": base["seed"],
        "scenario": scenario_id if scenario_id in SCENARIOS else "structural_collapse",
        "search_strategy": "adaptive",
    }
    data.update(overrides)
    return SimulationConfig(**data)


def list_scenarios() -> list[dict]:
    rows = []
    for key, item in SCENARIOS.items():
        rows.append(
            {
                "id": key,
                "label": item["label"],
                "summary": item["summary"],
                "width": item["width"],
                "height": item["height"],
                "survivor_x": item["survivor_x"],
                "survivor_y": item["survivor_y"],
                "noise_level": item["noise_level"],
                "response_probability": item["response_probability"],
                "sensor_reliability": item["sensor_reliability"],
                "seed": item["seed"],
            }
        )
    return rows
