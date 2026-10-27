import type { HeatPoint, OperationsSnapshot } from '../../types/operations'

export const APP_VERSION = '0.2.0'

export function panelState(mode: string | null | undefined, stale = false): string {
  if (stale) return 'STALE'
  if (mode === 'live') return 'LIVE'
  if (mode === 'replay') return 'REPLAY'
  if (mode === 'simulation') return 'SIMULATION'
  if (mode === 'manual') return 'MANUAL'
  return 'DISCONNECTED'
}

export function footerMode(snapshot: OperationsSnapshot | null): string {
  if (snapshot?.mode === 'live') return 'DEVICE'
  if (snapshot?.mode === 'replay') return 'REPLAY'
  if (snapshot?.mode === 'simulation' || snapshot?.legacy_simulation_active) return 'SIMULATION'
  return 'DISCONNECTED'
}

export function clockLabel(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function snapshotAge(snapshot: OperationsSnapshot | null): string {
  if (!snapshot) return 'no snapshot'
  if (snapshot.mode === 'replay') return 'fixture clock'
  const parsed = Date.parse(snapshot.updated_at_utc)
  if (!Number.isFinite(parsed)) return '—'
  const seconds = Math.max(0, Math.round((Date.now() - parsed) / 1000))
  return seconds < 90 ? `${seconds}s snapshot` : `${Math.round(seconds / 60)}m snapshot`
}

export function sampledCount(snapshot: OperationsSnapshot | null): number {
  return (snapshot?.heatmap_points ?? []).filter((point) => point.sample_count > 0 && !point.interpolated).length
}

export function nvidiaLive(snapshot: OperationsSnapshot | null): boolean {
  return Boolean(
    snapshot?.nvidia_online &&
      snapshot.reasoning?.provider === 'nebius_token_factory' &&
      snapshot.reasoning.live_call,
  )
}

export function evidenceHeadline(snapshot: OperationsSnapshot | null): string {
  const narrative = snapshot?.reasoning?.narrative?.trim()
  if (narrative) return narrative.split(/(?<=\.)\s/)[0] || narrative
  const label = snapshot?.impulse?.class || snapshot?.acoustic?.class
  if (!label || label === 'silence' || label === 'ambient' || label === 'unknown') return 'No classified event'
  if (label === 'knock' || label === 'tap') return 'Knock candidate'
  return label
}

export function deviceOnline(snapshot: OperationsSnapshot | null): { online: number; total: number } {
  const devices = snapshot?.devices ?? []
  return {
    online: devices.filter((device) => device.state === 'connected' || device.state === 'simulated').length,
    total: devices.length,
  }
}

export const DEVICE_LABELS: Record<string, string> = {
  raspberry_pi_4: 'Raspberry Pi 4',
  camera_top: 'Camera',
  camera_ground_coordinate: 'Camera 2 · Ground Coordinate',
  camera_ground_inspection: 'Camera 3 · Ground Inspection',
  arduino_uno: 'Arduino Uno',
  arduino_mega: 'Arduino Mega 2560',
  esp32: 'ESP32',
  mr60bha2: 'MR60BHA2',
  hc_sr04: 'HC-SR04',
  xvf3800: 'ReSpeaker XVF3800',
  piezo: 'Piezo acquisition',
  solenoid: 'Solenoid / MOSFET',
  bluetooth: 'Bluetooth',
  nebius_nvidia: 'Nebius NVIDIA advisory',
}

export function pointDetail(point: HeatPoint | undefined): string {
  if (!point) return 'No samples at this marker.'
  const score = point.score === null ? 'unknown' : String(point.score)
  return `${point.x_cm} cm, ${point.y_cm} cm · ${point.sample_count} samples · ${score} (${point.score_semantics}) · ${point.interpolated ? 'interpolated' : 'measured'} · ${point.source_mode}`
}

export function cameraShort(cameraId: string): string {
  if (cameraId === 'camera_top') return 'Camera'
  if (cameraId === 'camera_ground_coordinate') return 'Coordinate'
  if (cameraId === 'camera_ground_inspection') return 'Inspection'
  return cameraId
}
