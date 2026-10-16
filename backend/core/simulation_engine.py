"""World container for one mission. Sensor simulators live here; search code never reads the hidden source."""

from __future__ import annotations

from models.mission import FusionResult, SimulationConfig
from models.sensors import AudioReading, CameraObservation, RawObservation, VibrationReading
from reasoning.probability_map import ProbabilityMap
from reasoning.sensor_fusion import fuse
from simulation.acoustic import generate_audio
from simulation.camera import SimulatedCameraAdapter
from simulation.environment import Environment
from simulation.piezo import generate_vibration
from simulation.robot import SimulatedMotionAdapter
from simulation.striker import SimulatedStrikerAdapter
from simulation.survivor import observe, probe_rng


class SimulationEngine:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.environment = Environment(config)
        self.belief = ProbabilityMap(config.width, config.height)
        self.camera = SimulatedCameraAdapter()
        self.motion = SimulatedMotionAdapter()
        self.striker = SimulatedStrikerAdapter()

    def see(self, x: float, y: float) -> CameraObservation:
        return self.camera.observe(self.environment, x, y)

    def measure(
        self,
        x: float,
        y: float,
        profile: dict | None = None,
    ) -> tuple[RawObservation, FusionResult, AudioReading, VibrationReading]:
        if profile is None:
            observation = observe(self.environment, x, y, self.config)
        else:
            observation = RawObservation(
                audio=profile["audio"],
                vibration=profile["vibration"],
                cavity=profile["cavity"],
                visual=profile["visual"],
                audio_state=profile["audio_state"],
                distance=self.environment.distance_to_survivor(x, y),
            )
        fused = fuse(observation)
        rng = probe_rng(self.config.seed, x, y)
        audio = generate_audio(observation.audio_state, observation.audio, rng)
        vibration = generate_vibration(observation.vibration, observation.cavity, rng)
        self.striker.knock(vibration)
        return observation, fused, audio, vibration
