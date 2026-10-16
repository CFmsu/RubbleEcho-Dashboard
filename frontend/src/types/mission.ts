export interface FusionResult {
  audio: number;
  vibration: number;
  cavity: number;
  visual: number;
  combined: number;
  weights: Record<string, number>;
}

export interface Waveform {
  samples: number[];
  sample_rate_hz: number;
  duration_s: number;
}

export interface AudioReading {
  state: string;
  confidence: number;
  label: string;
  waveform: Waveform;
  peak: number;
  energy: number;
}

export interface VibrationReading {
  peak_amplitude: number;
  signal_energy: number;
  cavity_response: number;
  confidence: number;
  dominant_frequency_hz: number;
  waveform: Waveform;
}

export interface CameraObservation {
  surface_type: string;
  debris_density: number;
  visible_void: boolean;
  safe_to_probe: boolean;
  note: string;
}

export interface RobotState {
  x: number;
  y: number;
  heading: number;
  velocity: number;
  battery: number;
  state: string;
  phase: string;
  current_target_x: number | null;
  current_target_y: number | null;
  probe_count: number;
  distance_travelled: number;
  trail: number[][];
}

export interface MissionEvent {
  time: number;
  message: string;
  level: "info" | "warn" | "alert" | "good";
}

export interface SearchDecision {
  observation: string;
  decision: string;
  reason: string;
  confidence: number;
  target_x: number | null;
  target_y: number | null;
  provider: string;
}

export interface ProbePoint {
  id: string;
  x: number;
  y: number;
  confidence: number;
  audio_state: string;
  vibration_confidence: number;
  cavity_confidence: number;
  is_confirmation: boolean;
}

export interface StrategyStats {
  measurements: number;
  distance_travelled: number;
  simulated_minutes: number;
  found: boolean;
}

export interface ComparisonResult {
  grid: StrategyStats;
  adaptive: StrategyStats;
  note: string;
}

export interface CandidateLocation {
  x: number;
  y: number;
  confidence: number;
  status: string;
}

export interface MissionView {
  id: string;
  status: "IDLE" | "ACTIVE" | "PAUSED" | "COMPLETE";
  scenario: string;
  scenario_label: string;
  robot_state: string;
  runtime: number;
  probe_count: number;
  highest_confidence: number;
  phase: string;
  phase_progress: number;
  demo_mode: boolean;
  search_strategy: "grid" | "adaptive";
  speed: number;
  width: number;
  height: number;
  activity_step: string;
  candidate: CandidateLocation | null;
  outcome: string | null;
}

export interface HardwareItem {
  name: string;
  status: string;
}

export interface TelemetrySnapshot {
  type: "telemetry";
  timestamp: number;
  mission: MissionView;
  robot: RobotState;
  sensors: {
    audio: AudioReading | null;
    vibration: VibrationReading | null;
    camera: CameraObservation | null;
    fusion: FusionResult | null;
  };
  probability_map: number[][];
  probes: ProbePoint[];
  decision: SearchDecision;
  events: MissionEvent[];
  comparison: ComparisonResult | null;
  hardware: HardwareItem[];
  mode: "simulation";
}

export interface SimulationConfig {
  width: number;
  height: number;
  survivor_x: number;
  survivor_y: number;
  noise_level: number;
  response_probability: number;
  sensor_reliability: number;
  search_strategy: "grid" | "adaptive";
  seed: number;
  scenario: string;
  speed: number;
  demo_mode: boolean;
}

export interface ScenarioPreset {
  id: string;
  label: string;
  summary: string;
  width: number;
  height: number;
  survivor_x: number;
  survivor_y: number;
  noise_level: number;
  response_probability: number;
  sensor_reliability: number;
  seed: number;
}

export interface LabResult {
  stimulus: string;
  audio: AudioReading;
  vibration: VibrationReading;
  fusion: FusionResult;
  features: {
    audio_state: string;
    audio_label: string;
    peak_amplitude: number;
    signal_energy: number;
    cavity_response: number;
    dominant_frequency_hz: number;
  };
  note: string;
}

export type PageId = "dashboard" | "field" | "simulation" | "lab" | "bench" | "architecture" | "about";
export type ConnectionStatus = "connecting" | "connected" | "disconnected";
