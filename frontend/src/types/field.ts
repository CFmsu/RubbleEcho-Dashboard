export type CellClassification =
  | "debris_covered"
  | "obstructed"
  | "clear_surface"
  | "possible_opening"
  | "uncertain";

export interface GridCell {
  cell: string;
  classification: CellClassification;
  observation: string;
  uncertainty: "low" | "medium" | "high";
  source: "unanalyzed" | "model" | "manual_correction";
}

export interface VisionAnalysis {
  model_id: string;
  request_status: "succeeded" | "failed" | "not_run";
  error: string | null;
  summary: string;
  limitations: string[];
  cells: GridCell[];
}

export interface SectorRecommendation {
  cell: string;
  priority: number;
  reason: string;
  evidence: string[];
  uncertainty: string;
  next_action: string;
}

export interface ReasoningResult {
  model_id: string | null;
  image_input_used: boolean;
  request_status: "succeeded" | "failed" | "not_run";
  error: string | null;
  priorities: SectorRecommendation[];
  uncertainties: string[];
  cannot_infer: string[];
}

export interface FieldObservation {
  id: string;
  source: string;
  filename: string;
  media_type: string;
  created_at: string;
  width: number;
  height: number;
  cells: GridCell[];
  analysis: VisionAnalysis;
  reasoning: ReasoningResult;
}

export interface HardwareEvent {
  device_id: string;
  event_id: string;
  event_type: string;
  sequence: number;
  uptime_ms: number;
  label: string;
  received_at: string;
  port: string;
}

export interface BenchSample {
  source: "REAL_HARDWARE";
  sensor_id: string;
  sequence: number;
  timestamp: string;
  device_ms: number | null;
  flex_raw: number | null;
  light_pocket_raw: number | null;
  light_reference_raw: number | null;
  thermistor_raw: number | null;
  pir_left: number | null;
  pir_right: number | null;
  pir_ready: boolean | null;
  heading_deg: number | null;
  range_pw_us: number | null;
  range_cm: number | null;
  range_status: string | null;
}

export interface DistanceReading {
  device_id: string;
  event_id: string;
  distance_cm: number | null;
  timestamp: string;
  sequence: number;
  sensor_id: string;
  source: "REAL_HARDWARE";
  received_at: string;
  port: string;
}

export interface SerialPort {
  device: string;
  description: string;
  hwid: string;
}

export interface FieldSnapshot {
  type: "field";
  operating_mode: "demo" | "real";
  nebius_configured: boolean;
  warnings: string[];
  cells: string[];
  observations: FieldObservation[];
  hardware: {
    state: "CONNECTED" | "DISCONNECTED";
    link_status: "CONNECTED" | "STALE" | "DISCONNECTED";
    bench_status?: "CONNECTED" | "STALE" | "WAITING" | "DISCONNECTED";
    port: string | null;
    baud: number;
    error: string | null;
    event_count: number;
    distance_count: number;
    bench_count?: number;
    ultrasonic_enabled: boolean;
    events: HardwareEvent[];
    distances: DistanceReading[];
    bench?: BenchSample[];
    notes: string[];
    ports: SerialPort[];
  };
}
