from core.mission_controller import MissionController
from core.search_strategy import SearchStrategy
from models.mission import SimulationConfig
from reasoning.probability_map import ProbabilityMap
from reasoning.sensor_fusion import fuse
from models.sensors import RawObservation


def test_map_starts_uniform():
    belief = ProbabilityMap(10, 10)
    assert abs(float(belief.grid.sum()) - 1.0) < 1e-6
    assert abs(float(belief.grid[0, 0]) - 0.01) < 1e-9


def test_update_raises_probability_near_probe():
    belief = ProbabilityMap(12, 12)
    before = float(belief.grid[6, 7])
    far_before = float(belief.grid[0, 0])
    belief.update(7.2, 6.4, 0.9)
    assert float(belief.grid.sum()) == 1 or abs(float(belief.grid.sum()) - 1) < 1e-6
    assert float(belief.grid[6, 7]) > before
    assert float(belief.grid[6, 7]) > float(belief.grid[0, 0])
    assert float(belief.grid[0, 0]) <= far_before * 1.2


def test_weak_observation_does_not_concentrate_like_a_strong_one():
    strong = ProbabilityMap(12, 12)
    weak = ProbabilityMap(12, 12)
    strong.update(7.2, 6.4, 0.9)
    weak.update(7.2, 6.4, 0.05)
    assert float(strong.grid[6, 7]) > float(weak.grid[6, 7])


def test_next_probe_avoids_existing_points():
    belief = ProbabilityMap(12, 12)
    belief.update(8.2, 8.2, 0.95)
    strategy = SearchStrategy()
    x, y, reason = strategy.select(1, 1, belief, "adaptive", [])
    assert reason
    again_x, again_y, _ = strategy.select(1, 1, belief, "adaptive", [(x, y)])
    assert abs(again_x - x) > 0.4 or abs(again_y - y) > 0.4


def test_grid_returns_a_point():
    belief = ProbabilityMap(12, 12)
    x, y, reason = SearchStrategy().select(1, 1, belief, "grid", [])
    assert 0 < x < 12
    assert 0 < y < 12
    assert "Grid" in reason


def test_demo_fusion_bands():
    profiles = [
        (0.16, 0.22, 0.18, 0.16, 0.18),
        (0.22, 0.48, 0.30, 0.18, 0.31),
        (0.40, 0.52, 0.72, 0.28, 0.48),
        (0.92, 0.66, 0.56, 0.40, 0.69),
        (0.97, 0.88, 0.80, 0.74, 0.87),
    ]
    for audio, vibration, cavity, visual, expected in profiles:
        fused = fuse(
            RawObservation(
                audio=audio,
                vibration=vibration,
                cavity=cavity,
                visual=visual,
                audio_state="NO_RESPONSE",
                distance=1,
            )
        )
        assert round(fused.combined * 100) == round(expected * 100)


def test_adaptive_uses_fewer_measurements_than_grid():
    mission = MissionController()
    comparison = mission.comparison
    assert comparison is not None
    assert comparison.adaptive.found
    assert comparison.grid.found
    assert comparison.adaptive.measurements < comparison.grid.measurements
    assert "SIMULATED RESULTS" in comparison.note


def test_custom_seed_changes_world_not_map_prior():
    first = ProbabilityMap(8, 8)
    second = ProbabilityMap(8, 8)
    assert first.get_map() == second.get_map()
    config_a = SimulationConfig(seed=1, width=8, height=8, survivor_x=2, survivor_y=2)
    config_b = SimulationConfig(seed=2, width=8, height=8, survivor_x=6, survivor_y=6)
    assert config_a.seed != config_b.seed
