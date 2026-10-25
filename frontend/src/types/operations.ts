export type SourceMode = 'live' | 'replay' | 'simulation' | 'manual' | 'unavailable'
export type Badge = 'LIVE' | 'REPLAY' | 'SIMULATION' | 'MANUAL' | 'DISCONNECTED'

export interface DeviceStatus {
  device_id: string
  device_type: string
  source_mode: SourceMode
  state: string
  last_seen_utc: string | null
  age_ms: number | null
  quality: string
  error: string | null
  firmware?: string | null
}

export interface CameraCard {
  camera_id: string
  name: string
  panoramic_360: boolean
  state: string
  source_mode: SourceMode
  fps: number | null
  width: number | null
  height: number | null
  last_frame_utc: string | null
  error: string | null
  image_url?: string | null
}

export interface RadarObservation {
  human_presence: boolean | null
  distance_m: number | null
  breath_rate_bpm: number | null
  heart_rate_bpm: number | null
  num_targets?: number | null
  illuminance_lx?: number | null
  breath_phase?: number | null
  heart_phase?: number | null
  total_phase: number | null
  stability: string | null
  stale: boolean
  valid: boolean
  target_xy_m: number[] | null
  spatial_coordinates_used: boolean
  firmware: string | null
  notes: string[]
  captured_at_utc: string | null
  source_mode: SourceMode
  display_bearing_deg?: number | null
  case_name?: string | null
}

export interface HeatPoint {
  point_id: string
  x_cm: number
  y_cm: number
  score: number | null
  score_semantics: string
  interpolated: boolean
  sample_count: number
  method: string
  source_mode: SourceMode
  quality: string
  evidence_event_ids: string[]
}

export interface OpsEvent {
  event_id: string
  mode: string
  device?: string
  sensor?: string
  summary?: string
  quality?: string
  captured_at_utc?: string | null
  value?: number | string | boolean | null
  unit?: string | null
  site_id?: string | null
}

export interface Reasoning {
  provider: string
  summary: string
  nvidia_online: boolean
  live_call?: boolean
  model_id?: string | null
  latency_ms?: number | null
  score_semantics?: string
  validation_status?: string
  hypotheses: Array<{
    label: string
    score: number | null
    limitations: string[]
    evidence_event_ids: string[]
  }>
  recommendation: {
    type: string
    point_id: string | null
    requires_approval: boolean
    detail?: string
  }
  unknowns: string[]
  event_ids: string[]
}

export interface OperationsSnapshot {
  version: string
  badge: Badge
  mode: SourceMode
  system_live: boolean
  mission_phase: string
  safety_state: string
  run_active?: boolean
  scan_stage?: string
  run_elapsed_s?: number
  nvidia_online: boolean
  ai: {
    status: string
    model_id: string | null
    vision_model_id?: string | null
    message: string
    nvidia_online: boolean
  }
  devices: DeviceStatus[]
  cameras: CameraCard[]
  streaming_camera_count: number
  camera_count: number
  radar: RadarObservation | null
  ultrasonic: {
    distance_cm: number | null
    echo_timeout: boolean
    direction: string
    quality: string
    source_mode: SourceMode
  } | null
  acoustic: {
    class: string
    rms_dbfs: number | null
    model_score: number | null
    score_semantics: string
    origin_unknown: boolean
    site_id?: string | null
    source_mode: SourceMode
    channel_note?: string
    tdoa_summary?: string
    duration_ms?: number
  } | null
  impulse: {
    class: string
    model_score: number | null
    site_id?: string | null
    score_semantics: string
  } | null
  piezo: {
    peak_adc_counts: number
    rms_adc_counts: number
    unit: string
    contact_state: string
    site_id: string | null
    clipped: boolean
    source_mode: SourceMode
    acceleration_g: null
  } | null
  pose: {
    x_cm: number | null
    y_cm: number | null
    heading_deg: number | null
    source: string
    valid: boolean
    error_cm: number | null
    note?: string
  } | null
  pose_trail: Array<{ x_cm: number | null; y_cm: number | null; source: string; valid: boolean }>
  solenoid: {
    state: string
    output_energized: boolean
    physically_confirmed: boolean
    reference_sensor: string
    fault: string | null
    note: string
    pulses_logged: number
  }
  heatmap_points: HeatPoint[]
  events: OpsEvent[]
  reasoning: Reasoning | null
  search_plan?: SearchPlan | null
  scene_note?: { scene: string; obstacles: string[]; open_area: string } | null
  ai_usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
    estimated_usd: number
    calls: Array<{
      stage: string
      model_id: string
      prompt_tokens: number
      completion_tokens: number
      total_tokens: number
      estimated_usd: number | null
    }>
  }
  geometry_revision: string
  limitations: string[]
  updated_at_utc: string
  calibration: {
    marker_count: number
    homography_valid: boolean
    pose_valid: boolean
    rms_px: number | null
    reason: string
  }
  acoustic_envelope_dbfs: number[]
  acoustic_envelope_note: string
  impulse_envelope_dbfs: number[]
  operator_output_locked: boolean
  trial_id: string | null
  legacy_simulation_active: boolean
  malformed_radar_lines?: number
}

export interface SearchPlan {
  source: string
  execute_hardware: boolean
  look: string
  path: string[]
  note?: string
  camera_frame: string
  boundary: Array<{ x1_cm: number; y1_cm: number; x2_cm: number; y2_cm: number }>
  cells: Array<{ point_id: string; x_cm: number; y_cm: number; state: string }>
}

export interface TableGeometry {
  units: string
  geometry_revision: string
  coupling_note: string
  outer_cm: { width: number; height: number }
  inner_cm: { width: number; height: number; origin_x_cm: number; origin_y_cm: number }
  boxes: Array<{
    id: string
    role: string
    plan_width_cm: number
    plan_height_cm: number
    center_cm: { x: number; y: number }
  }>
  measurement_points: Array<{ id: string; x_cm: number; y_cm: number; box_id: string }>
  sand: {
    thick: { cover_above_lids_cm: number }
    thin: { cover_above_lids_cm: number }
  }
}

const badges: Badge[] = ['LIVE', 'REPLAY', 'SIMULATION', 'MANUAL', 'DISCONNECTED']

export function isOperationsSnapshot(value: unknown): value is OperationsSnapshot {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return (
    record.version === '1' &&
    typeof record.badge === 'string' &&
    badges.includes(record.badge as Badge) &&
    typeof record.mode === 'string' &&
    Array.isArray(record.devices) &&
    Array.isArray(record.cameras) &&
    Array.isArray(record.events)
  )
}
