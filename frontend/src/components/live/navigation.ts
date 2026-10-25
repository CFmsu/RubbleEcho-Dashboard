import type { OperationsSnapshot, TableGeometry } from '../../types/operations'

export const POINT_SECONDS = 5

export interface MapPoint {
  id: string
  x_cm: number
  y_cm: number
}

export interface RoverFix {
  x: number
  y: number
  heading: number
  fromId: string
  toId: string
  moving: boolean
}

export function heatColor(score: number | null): string {
  if (score === null) return '#8b98a8'
  if (score < 0.3) return '#16845d'
  if (score < 0.6) return '#b7791f'
  return '#c83a3a'
}

export function heatLabel(score: number | null): string {
  if (score === null) return 'Not sampled'
  if (score < 0.3) return 'Quiet control'
  if (score < 0.6) return 'Moderate case'
  return 'Strong case'
}

function headingDeg(from: MapPoint, to: MapPoint): number {
  if (from.x_cm === to.x_cm && from.y_cm === to.y_cm) return 0
  return (Math.atan2(to.y_cm - from.y_cm, to.x_cm - from.x_cm) * 180) / Math.PI
}

export function roverFix(
  geometry: TableGeometry,
  snapshot: OperationsSnapshot | null,
  elapsedSeconds?: number,
): RoverFix | null {
  const points = geometry.measurement_points
  if (!snapshot || snapshot.mode !== 'simulation' || points.length === 0) return null
  if (!snapshot.run_active && snapshot.mission_phase !== 'COMPLETE') return null
  const last = points.length - 1
  const approach = headingDeg(points[Math.max(0, last - 1)], points[last])
  if (!snapshot.run_active) {
    const parked = points[last]
    return { x: parked.x_cm, y: parked.y_cm, heading: approach, fromId: parked.id, toId: parked.id, moving: false }
  }
  const elapsed = elapsedSeconds ?? snapshot.run_elapsed_s ?? 0
  const segment = Math.min(last, Math.max(0, Math.floor(elapsed / POINT_SECONDS)))
  const from = points[segment]
  const to = points[Math.min(last, segment + 1)]
  const span = from.id === to.id ? 1 : (elapsed % POINT_SECONDS) / POINT_SECONDS
  const x = from.x_cm + (to.x_cm - from.x_cm) * span
  const y = from.y_cm + (to.y_cm - from.y_cm) * span
  const heading = from.id === to.id ? approach : headingDeg(from, to)
  return { x, y, heading, fromId: from.id, toId: to.id, moving: from.id !== to.id }
}
