"""Mission state machine. Drives probe phases and publishes snapshots for the dashboard."""

from __future__ import annotations

import logging
import math
from pathlib import Path

from core.comparison import run_comparison
from core.search_strategy import SearchStrategy
from core.simulation_engine import SimulationEngine
from models.mission import (
    CandidateLocation,
    MissionEvent,
    MissionView,
    ProbePoint,
    RobotState,
    SearchDecision,
    SimulationConfig,
)
from models.sensors import RawObservation, SensorBundle
from models.telemetry import HardwareItem, TelemetryMessage
from reasoning.provider import SimulatedReasoningProvider
from simulation.scenarios import config_from_scenario, scenario_label

logger = logging.getLogger("rubbleecho.mission")

PHASE_SECONDS = {
    "CONTACT": 2.4,
    "KNOCKING": 2.6,
    "LISTENING": 6.2,
    "ANALYZING": 4.0,
    "UPDATING_MAP": 2.0,
    "SELECTING_TARGET": 2.2,
    "CONFIRMING": 2.0,
    "HUMAN_RESPONSE_DETECTED": 2.4,
    "LOCATION_IDENTIFIED": 0.0,
    "IDLE": 1.0,
}

DISPLAY_STATE = {
    "IDLE": "IDLE",
    "NAVIGATING": "NAVIGATING",
    "CONTACT": "PROBING",
    "KNOCKING": "KNOCKING",
    "LISTENING": "LISTENING",
    "ANALYZING": "ANALYZING",
    "UPDATING_MAP": "ANALYZING",
    "SELECTING_TARGET": "EXPLORING",
    "CONFIRMING": "CONFIRMING",
    "HUMAN_RESPONSE_DETECTED": "CONFIRMING",
    "LOCATION_IDENTIFIED": "TARGET FOUND",
}

ACTIVITY_STEP = {
    "IDLE": "MOVE",
    "NAVIGATING": "MOVE",
    "CONTACT": "CONTACT",
    "KNOCKING": "KNOCK",
    "LISTENING": "LISTEN",
    "ANALYZING": "ANALYZE",
    "UPDATING_MAP": "UPDATE",
    "SELECTING_TARGET": "SELECT",
    "CONFIRMING": "SELECT",
    "HUMAN_RESPONSE_DETECTED": "ANALYZE",
    "LOCATION_IDENTIFIED": "SELECT",
}

DEMO_PROBES = [
    {"target": (2.2, 1.8), "audio": 0.16, "vibration": 0.22, "cavity": 0.18, "visual": 0.16, "audio_state": "NO_RESPONSE"},
    {"target": (4.1, 3.4), "audio": 0.22, "vibration": 0.48, "cavity": 0.30, "visual": 0.18, "audio_state": "AMBIENT_NOISE"},
    {"target": (5.6, 4.9), "audio": 0.40, "vibration": 0.52, "cavity": 0.72, "visual": 0.28, "audio_state": "WEAK_RESPONSE"},
    {"target": (6.7, 5.9), "audio": 0.92, "vibration": 0.66, "cavity": 0.56, "visual": 0.40, "audio_state": "POSSIBLE_TAP"},
    {"target": (7.2, 6.4), "audio": 0.97, "vibration": 0.88, "cavity": 0.80, "visual": 0.74, "audio_state": "CONFIRMED_RESPONSE"},
]


class MissionController:
    def __init__(self) -> None:
        self._seq = 1
        self.config = config_from_scenario("structural_collapse")
        self.speed = 1.0
        self.strategy = SearchStrategy()
        self.reasoning = SimulatedReasoningProvider()
        self.engine = SimulationEngine(self.config)
        self.comparison = None
        self._reset_world()
        self.comparison = run_comparison(self.config)

    def configure(self, config: SimulationConfig) -> None:
        if self.status == "ACTIVE":
            raise RuntimeError("Pause or reset the mission before changing the scenario.")
        self.config = config
        self.speed = config.speed
        self._reset_world()
        self.comparison = run_comparison(self.config)
        self._log("Scenario generated. Hidden source remains inside the simulator.", "info")
        logger.info("scenario configured id=%s seed=%s", config.scenario, config.seed)

    def start(self, config: SimulationConfig | None = None, demo: bool = False) -> None:
        if config is not None:
            self.config = config
        if demo:
            self.config = self.config.model_copy(
                update={
                    "width": 12,
                    "height": 12,
                    "survivor_x": 7.2,
                    "survivor_y": 6.4,
                    "seed": 42,
                    "scenario": "structural_collapse",
                    "search_strategy": "adaptive",
                    "noise_level": 0.08,
                    "response_probability": 0.95,
                    "sensor_reliability": 0.95,
                    "demo_mode": True,
                    "speed": self.speed,
                }
            )
        self._reset_world()
        self.demo = demo
        self.mission_id = f"RE-{self._seq:03d}"
        self._seq += 1
        self.status = "ACTIVE"
        self.comparison = run_comparison(self.config)
        self._log(f"Mission {self.mission_id} initialized", "info")
        self._log("Robot deployed", "info")
        logger.info("mission start id=%s demo=%s strategy=%s", self.mission_id, demo, self.config.search_strategy)
        self._choose_target()
        self._enter("NAVIGATING")

    def pause(self) -> None:
        if self.status != "ACTIVE":
            return
        self.status = "PAUSED"
        self.velocity = 0.0
        self._log("Mission paused", "warn")
        logger.info("mission paused id=%s", self.mission_id)

    def resume(self) -> None:
        if self.status != "PAUSED":
            return
        self.status = "ACTIVE"
        self._log("Mission resumed", "info")
        logger.info("mission resumed id=%s", self.mission_id)

    def reset(self) -> None:
        speed = self.speed
        self.config = self.config.model_copy(update={"demo_mode": False})
        self._reset_world()
        self.speed = speed
        self.comparison = run_comparison(self.config)
        self._log("Mission reset", "info")
        logger.info("mission reset")

    def set_speed(self, speed: float) -> None:
        self.speed = float(min(10.0, max(0.5, speed)))

    def step(self) -> None:
        if self.status == "IDLE":
            raise RuntimeError("Start a mission before stepping.")
        if self.status == "COMPLETE":
            return
        was_paused = self.status == "PAUSED"
        self.status = "ACTIVE"
        remaining = max(0.0, self.phase_duration - self.phase_elapsed)
        self.tick(remaining + 1e-3)
        if was_paused and self.status == "ACTIVE":
            self.status = "PAUSED"
            self.velocity = 0.0

    def tick(self, dt: float) -> None:
        if self.status != "ACTIVE":
            return
        remaining = max(0.0, dt)
        guard = 0
        while remaining > 1e-6 and guard < 8 and self.status == "ACTIVE":
            guard += 1
            if self.phase == "LOCATION_IDENTIFIED":
                self.status = "COMPLETE"
                return
            need = max(0.0, self.phase_duration - self.phase_elapsed)
            step = min(remaining, need if need > 0 else remaining)
            self.sim_time += step
            self.phase_elapsed += step
            remaining -= step
            if self.phase == "NAVIGATING":
                self._update_motion()
            if self.phase_elapsed + 1e-9 >= self.phase_duration:
                self._complete_phase()
            else:
                break

    def snapshot(self) -> TelemetryMessage:
        progress = 0.0
        if self.phase_duration > 0:
            progress = min(1.0, self.phase_elapsed / self.phase_duration)
        mission = MissionView(
            id=self.mission_id,
            status=self.status,
            scenario=self.config.scenario,
            scenario_label=scenario_label(self.config.scenario),
            robot_state=self._display_state(),
            runtime=round(self.sim_time, 2),
            probe_count=len(self.probes),
            highest_confidence=round(self.highest, 4),
            phase=self.phase,
            phase_progress=round(progress, 3),
            demo_mode=self.demo,
            search_strategy=self.config.search_strategy,
            speed=self.speed,
            width=self.config.width,
            height=self.config.height,
            activity_step=ACTIVITY_STEP.get(self.phase, "MOVE"),
            candidate=self.candidate,
            outcome=self.outcome,
        )
        robot = RobotState(
            x=round(self.x, 3),
            y=round(self.y, 3),
            heading=round(self.heading, 1),
            velocity=round(self.velocity, 3),
            battery=round(self.battery, 1),
            state=mission.robot_state,
            phase=self.phase,
            current_target_x=None if self.target is None else round(self.target[0], 3),
            current_target_y=None if self.target is None else round(self.target[1], 3),
            probe_count=len(self.probes),
            distance_travelled=round(self.distance, 2),
            trail=self.trail[-240:],
        )
        return TelemetryMessage(
            timestamp=round(self.sim_time, 2),
            mission=mission,
            robot=robot,
            sensors=SensorBundle(
                audio=self.audio,
                vibration=self.vibration,
                camera=self.camera,
                fusion=self.fusion,
            ),
            probability_map=self.engine.belief.get_map(),
            probes=self.probes,
            decision=self.decision,
            events=self.events[-60:],
            comparison=self.comparison,
            hardware=self._hardware(),
        )

    def _reset_world(self) -> None:
        self.engine = SimulationEngine(self.config)
        self.status = "IDLE"
        self.mission_id = f"RE-{self._seq:03d}"
        self.sim_time = 0.0
        self.events = []
        self.probes = []
        self.phase = "IDLE"
        self.phase_elapsed = 0.0
        self.phase_duration = 1.0
        self.x, self.y = _start(self.config)
        self.heading = 45.0
        self.velocity = 0.0
        self.battery = 100.0
        self.distance = 0.0
        self.trail = [[round(self.x, 3), round(self.y, 3)]]
        self.target: tuple[float, float] | None = None
        self.nav_start: tuple[float, float] | None = None
        self.observation: RawObservation | None = None
        self.fusion = None
        self.audio = None
        self.vibration = None
        self.camera = None
        self.highest = 0.0
        self.demo = False
        self.demo_index = 0
        self.pending_profile: dict | None = None
        self.confirmation_leg = False
        self.candidate = None
        self.outcome = None
        self.decision = SearchDecision(
            observation="Mission is standing by in simulation mode.",
            decision="Awaiting start.",
            reason="No probe has been selected.",
            confidence=0.0,
            provider="SIMULATED",
        )

    def _enter(self, phase: str) -> None:
        self.phase = phase
        self.phase_elapsed = 0.0
        self.phase_duration = self._duration(phase)
        self.velocity = self.engine.motion.speed_mps if phase == "NAVIGATING" else 0.0
        logger.info("phase %s t=%.1f probes=%s", phase, self.sim_time, len(self.probes))

        if phase == "NAVIGATING" and self.target is not None:
            self.nav_start = (self.x, self.y)
            self.heading = self.engine.motion.heading(self.x, self.y, self.target[0], self.target[1])
            self._log(f"Navigating toward probe P{len(self.probes) + 1:02d}", "info")
        elif phase == "CONTACT" and self.target is not None:
            self._snap_to_target()
            self.camera = self.engine.see(self.x, self.y)
            self._log("Surface contact established", "info")
        elif phase == "KNOCKING":
            self._log(f"Knock initiated at probe P{len(self.probes) + 1:02d}", "info")
            self.battery = max(8.0, self.battery - 1.6)
        elif phase == "LISTENING":
            self._capture()
            self._log("Listening window opened", "info")
        elif phase == "ANALYZING":
            self._log_analysis()
        elif phase == "UPDATING_MAP" and self.fusion is not None:
            self.engine.belief.update(self.x, self.y, self.fusion.combined)
            self.highest = max(self.highest, self.fusion.combined)
            self._log("Probability map updated", "info")
            self._log(f"Highest simulation confidence is now {self.highest:.2f}", "info")
        elif phase == "CONFIRMING":
            self._log("Confirmation probe initiated", "alert")
        elif phase == "HUMAN_RESPONSE_DETECTED":
            self._log("Human response detected", "good")
            self._log(f"Confidence increased to {self.highest:.2f}", "good")
        elif phase == "LOCATION_IDENTIFIED":
            self._mark_candidate()
            self.status = "COMPLETE"
            self.velocity = 0.0
            self._persist()

    def _complete_phase(self) -> None:
        phase = self.phase
        if phase == "NAVIGATING":
            self._snap_to_target()
            self._enter("CONTACT")
        elif phase == "CONTACT":
            self._enter("KNOCKING")
        elif phase == "KNOCKING":
            self._enter("LISTENING")
        elif phase == "LISTENING":
            self._enter("ANALYZING")
        elif phase == "ANALYZING":
            self._enter("UPDATING_MAP")
        elif phase == "UPDATING_MAP":
            self._after_update()
        elif phase == "SELECTING_TARGET":
            self._enter("NAVIGATING")
        elif phase == "CONFIRMING":
            self._enter("NAVIGATING")
        elif phase == "HUMAN_RESPONSE_DETECTED":
            self._enter("LOCATION_IDENTIFIED")
        elif phase == "LOCATION_IDENTIFIED":
            self.status = "COMPLETE"

    def _after_update(self) -> None:
        if self.observation is None or self.fusion is None:
            self._choose_target()
            self._enter("SELECTING_TARGET")
            return
        positive = self.observation.audio_state in {"POSSIBLE_TAP", "CONFIRMED_RESPONSE"} and self.fusion.combined >= 0.6
        confirmed = self.observation.audio_state == "CONFIRMED_RESPONSE" and self.fusion.combined >= 0.8
        if self.confirmation_leg and (confirmed or (positive and self.fusion.combined >= 0.75)):
            self.confirmation_leg = False
            self._enter("HUMAN_RESPONSE_DETECTED")
            return
        if self.confirmation_leg:
            self.confirmation_leg = False
            self._log("Confirmation probe did not repeat the response. Search continues.", "warn")
        elif positive:
            self._arm_confirmation()
            self._enter("CONFIRMING")
            return
        if len(self.probes) >= max(18, (self.config.width * self.config.height) // 2):
            self.outcome = "SEARCH INCOMPLETE"
            self._log("Survey limit reached before confirmation.", "warn")
            self.status = "COMPLETE"
            self.phase = "IDLE"
            return
        self._choose_target()
        self._enter("SELECTING_TARGET")

    def _choose_target(self) -> None:
        reason = "Highest information value among unexplored cells."
        if self.demo and self.demo_index < len(DEMO_PROBES):
            profile = DEMO_PROBES[self.demo_index]
            self.demo_index += 1
            self.pending_profile = profile
            self.target = profile["target"]
            reason = "Demo sequence: next probe follows the rising evidence."
        else:
            self.pending_profile = None
            visited = [(probe.x, probe.y) for probe in self.probes]
            target_x, target_y, reason = self.strategy.select(
                self.x,
                self.y,
                self.engine.belief,
                self.config.search_strategy,
                visited,
            )
            self.target = (target_x, target_y)
        self._publish_decision(reason)
        self._log(f"Probe P{len(self.probes) + 1:02d} selected", "info")

    def _arm_confirmation(self) -> None:
        self.confirmation_leg = True
        if self.demo and self.demo_index < len(DEMO_PROBES):
            profile = DEMO_PROBES[self.demo_index]
            self.demo_index += 1
            self.pending_profile = profile
            self.target = profile["target"]
            reason = "Confirmation probe beside the strongest acoustic evidence."
        else:
            self.pending_profile = None
            peak_x, peak_y, _peak = self.engine.belief.highest_probability()
            if math.hypot(peak_x - self.x, peak_y - self.y) <= 1.25:
                self.target = (peak_x, peak_y)
            else:
                self.target = (self.x, self.y)
            reason = "Confirmation probe at the contact that produced the response."
        self._publish_decision(reason)
        self._log(f"Probe P{len(self.probes) + 1:02d} selected for confirmation", "alert")

    def _capture(self) -> None:
        observation, fused, audio, vibration = self.engine.measure(self.x, self.y, self.pending_profile)
        self.observation = observation
        self.fusion = fused
        self.audio = audio
        self.vibration = vibration
        self.probes.append(
            ProbePoint(
                id=f"P{len(self.probes) + 1:02d}",
                x=round(self.x, 2),
                y=round(self.y, 2),
                confidence=fused.combined,
                audio_state=observation.audio_state,
                vibration_confidence=round(observation.vibration, 4),
                cavity_confidence=round(observation.cavity, 4),
                is_confirmation=self.confirmation_leg,
            )
        )
        logger.info(
            "probe %s audio=%s fusion=%.2f",
            self.probes[-1].id,
            observation.audio_state,
            fused.combined,
        )

    def _log_analysis(self) -> None:
        if self.observation is None or self.fusion is None:
            return
        state = self.observation.audio_state
        if state == "CONFIRMED_RESPONSE":
            self._log("Acoustic response detected", "good")
        elif state == "POSSIBLE_TAP":
            self._log("Possible human response detected", "alert")
        elif state == "WEAK_RESPONSE":
            self._log("Weak acoustic event recorded", "warn")
        elif self.observation.vibration >= 0.4:
            self._log("Vibration anomaly detected", "warn")
        else:
            self._log("No human response detected", "info")
        if self.observation.cavity >= 0.55:
            self._log("Possible cavity identified", "warn")
        self._publish_decision(self.decision.reason)

    def _publish_decision(self, reason: str) -> None:
        observation = self.observation or RawObservation(
            audio=0.0,
            vibration=0.0,
            cavity=0.0,
            visual=0.0,
            audio_state="NO_RESPONSE",
            distance=0.0,
        )
        target_x = None if self.target is None else self.target[0]
        target_y = None if self.target is None else self.target[1]
        self.decision = self.reasoning.decide_next_action(observation, target_x, target_y, reason)
        logger.info("decision %s", self.decision.decision)

    def _mark_candidate(self) -> None:
        if self.probes:
            cx, cy = self.probes[-1].x, self.probes[-1].y
        else:
            cx, cy = self.engine.belief.centroid()
        confidence = self.highest
        self.candidate = CandidateLocation(
            x=round(cx, 1),
            y=round(cy, 1),
            confidence=round(confidence, 4),
        )
        self.outcome = "SURVIVOR LOCATION IDENTIFIED"
        self._log("Candidate survivor location marked", "good")
        self._log("Awaiting rescue team verification", "alert")
        logger.info("candidate marked x=%.1f y=%.1f confidence=%.2f", cx, cy, confidence)

    def _update_motion(self) -> None:
        if self.target is None or self.nav_start is None or self.phase_duration <= 0:
            return
        fraction = min(1.0, self.phase_elapsed / self.phase_duration)
        nx, ny = self.engine.motion.interpolate(self.nav_start[0], self.nav_start[1], self.target[0], self.target[1], fraction)
        moved = math.hypot(nx - self.x, ny - self.y)
        self.distance += moved
        self.battery = max(8.0, self.battery - moved * 0.08)
        self.x, self.y = nx, ny
        self.heading = self.engine.motion.heading(self.nav_start[0], self.nav_start[1], self.target[0], self.target[1])
        self._push_trail()

    def _snap_to_target(self) -> None:
        if self.target is None:
            return
        self.distance += math.hypot(self.target[0] - self.x, self.target[1] - self.y)
        self.x, self.y = self.target
        self._push_trail()

    def _push_trail(self) -> None:
        if not self.trail or math.hypot(self.x - self.trail[-1][0], self.y - self.trail[-1][1]) >= 0.08:
            self.trail.append([round(self.x, 3), round(self.y, 3)])
            if len(self.trail) > 400:
                self.trail = self.trail[-400:]

    def _duration(self, phase: str) -> float:
        if phase == "NAVIGATING" and self.target is not None:
            distance = math.hypot(self.target[0] - self.x, self.target[1] - self.y)
            return self.engine.motion.travel_seconds(distance)
        return PHASE_SECONDS.get(phase, 1.0)

    def _display_state(self) -> str:
        if self.outcome == "SURVIVOR LOCATION IDENTIFIED":
            return "TARGET FOUND"
        if self.confirmation_leg and self.phase in {
            "NAVIGATING",
            "CONTACT",
            "KNOCKING",
            "LISTENING",
            "ANALYZING",
            "CONFIRMING",
        }:
            return "CONFIRMING"
        return DISPLAY_STATE.get(self.phase, "IDLE")

    def _hardware(self) -> list[HardwareItem]:
        microphone = "LISTENING" if self.phase == "LISTENING" else "ONLINE"
        striker = "FIRING" if self.phase == "KNOCKING" else "READY"
        mobility = "ONLINE" if self.status == "ACTIVE" else "STANDBY"
        return [
            HardwareItem(name="CAMERA", status="ONLINE"),
            HardwareItem(name="MICROPHONE", status=microphone),
            HardwareItem(name="PIEZO", status="ONLINE"),
            HardwareItem(name="STRIKER", status=striker),
            HardwareItem(name="MOBILITY", status=mobility),
            HardwareItem(name="AI ENGINE", status="SIMULATED"),
        ]

    def _log(self, message: str, level: str) -> None:
        self.events.append(MissionEvent(time=round(self.sim_time, 2), message=message, level=level))  # type: ignore[arg-type]
        if len(self.events) > 300:
            self.events = self.events[-300:]
        log_fn = logger.warning if level == "warn" else logger.info
        log_fn("t=%05.1f %s", self.sim_time, message)

    def _persist(self) -> None:
        try:
            path = Path(__file__).resolve().parents[1] / "data" / "last_mission.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.snapshot().model_dump_json(), encoding="utf-8")
        except OSError:
            logger.warning("mission snapshot could not be written")


def _start(config: SimulationConfig) -> tuple[float, float]:
    return min(1.0, config.width - 1.0), min(1.0, config.height - 1.0)
