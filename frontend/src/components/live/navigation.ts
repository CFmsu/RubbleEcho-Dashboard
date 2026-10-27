import type { OperationsSnapshot, TableGeometry } from '../../types/operations'

export const POINT_SECONDS = 1
export const CELL_SECONDS = 2

export interface MapPoint {
  id: string
  x_cm: number
  y_cm: number
  heading?: number
}

export interface GridCell extends MapPoint {
  row: number
  col: number
  originX: number
  originY: number
  width: number
  height: number
  border: number
  visit: number
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

export function gridCells(geometry: TableGeometry): GridCell[] {
  const inner = geometry.inner_cm
  const cellW = inner.width / 3
  const cellH = inner.height / 3
  const cells: GridCell[] = []
  for (let row = 0; row < 3; row += 1) {
    const columns = row % 2 === 0 ? [0, 1, 2] : [2, 1, 0]
    const heading = row % 2 === 0 ? 0 : 180
    for (const col of columns) {
      const x = Math.round((inner.origin_x_cm + (col + 0.5) * cellW) * 10) / 10
      const y = Math.round((inner.origin_y_cm + (row + 0.5) * cellH) * 10) / 10
      const border = heading === 0
        ? Math.round((inner.origin_x_cm + inner.width - x) * 10) / 10
        : Math.round((x - inner.origin_x_cm) * 10) / 10
      cells.push({
        id: `r${row + 1}c${col + 1}`,
        x_cm: x,
        y_cm: y,
        heading,
        row,
        col,
        originX: inner.origin_x_cm + col * cellW,
        originY: inner.origin_y_cm + row * cellH,
        width: cellW,
        height: cellH,
        border,
        visit: row * 3 + (row % 2 === 0 ? col : 2 - col) + 1,
      })
    }
  }
  return cells
}

export function siteInCell(geometry: TableGeometry, row: number, col: number): string | null {
  const inner = geometry.inner_cm
  const cellW = inner.width / 3
  const cellH = inner.height / 3
  for (const point of geometry.measurement_points) {
    const pointCol = Math.floor((point.x_cm - inner.origin_x_cm) / cellW)
    const pointRow = Math.floor((point.y_cm - inner.origin_y_cm) / cellH)
    if (pointRow === row && pointCol === col) return point.id
  }
  return null
}

export function driveRoute(geometry: TableGeometry, snapshot: OperationsSnapshot | null): MapPoint[] {
  const points = snapshot?.scan_route?.length ? snapshot.scan_route : gridCells(geometry)
  return points
    .filter((point) => !('blocked' in point && point.blocked))
    .map((point) => ({
      id: point.id,
      x_cm: point.x_cm,
      y_cm: point.y_cm,
      heading: 'heading_deg' in point && typeof point.heading_deg === 'number'
        ? point.heading_deg
        : 'heading' in point && typeof point.heading === 'number'
          ? point.heading
          : undefined,
    }))
}

export function echoFix(
  rover: RoverFix | null,
  distanceCm: number | null | undefined,
  echoTimeout: boolean,
  width: number,
  height: number,
): { x: number; y: number } | null {
  if (!rover || distanceCm == null || !Number.isFinite(distanceCm) || echoTimeout) return null
  const radians = (rover.heading * Math.PI) / 180
  return {
    x: Math.min(width - 1.4, Math.max(1.4, rover.x + Math.cos(radians) * distanceCm)),
    y: Math.min(height - 1.4, Math.max(1.4, rover.y + Math.sin(radians) * distanceCm)),
  }
}

function poseFix(snapshot: OperationsSnapshot): RoverFix | null {
  const pose = snapshot.pose
  if (!pose?.valid || pose.x_cm == null || pose.y_cm == null) return null
  const cell = pose.cell_id || 'pose'
  return {
    x: pose.x_cm,
    y: pose.y_cm,
    heading: pose.heading_deg ?? 0,
    fromId: cell,
    toId: cell,
    moving: false,
  }
}

function trackFix(snapshot: OperationsSnapshot, legElapsedMs?: number): RoverFix | null {
  const live = snapshot.pose?.source === 'arduino_uno'
  const leg = snapshot.rover_leg
  if (!live && !leg) return null
  if (leg && leg.duration_ms > 0) {
    const elapsed = legElapsedMs ?? leg.elapsed_ms
    const span = Math.min(1, Math.max(0, elapsed / leg.duration_ms))
    if (span < 1) {
      return {
        x: leg.from_x_cm + (leg.to_x_cm - leg.from_x_cm) * span,
        y: leg.from_y_cm + (leg.to_y_cm - leg.from_y_cm) * span,
        heading: leg.heading_deg,
        fromId: leg.from_id,
        toId: leg.to_id,
        moving: true,
      }
    }
  }
  return live ? poseFix(snapshot) : null
}

export function roverFix(
  geometry: TableGeometry,
  snapshot: OperationsSnapshot | null,
  elapsedSeconds?: number,
  legElapsedMs?: number,
): RoverFix | null {
  if (!snapshot) return null
  const tracked = trackFix(snapshot, legElapsedMs)
  if (tracked) return tracked
  if (snapshot.mode !== 'simulation') return poseFix(snapshot)
  const points = driveRoute(geometry, snapshot)
  if (points.length === 0) return null
  if (!snapshot.run_active && snapshot.mission_phase !== 'COMPLETE') return poseFix(snapshot)
  const last = points.length - 1
  const parked = points[last]
  if (!snapshot.run_active) {
    return { x: parked.x_cm, y: parked.y_cm, heading: parked.heading ?? 0, fromId: parked.id, toId: parked.id, moving: false }
  }
  const elapsed = elapsedSeconds ?? snapshot.run_elapsed_s ?? 0
  const cell = Math.min(last, Math.max(0, Math.floor(elapsed / CELL_SECONDS)))
  const local = (elapsed % CELL_SECONDS) / CELL_SECONDS
  const here = points[cell]
  const prev = points[Math.max(0, cell - 1)]
  if (cell > 0 && local < 0.4) {
    const span = local / 0.4
    return {
      x: prev.x_cm + (here.x_cm - prev.x_cm) * span,
      y: prev.y_cm + (here.y_cm - prev.y_cm) * span,
      heading: headingDeg(prev, here),
      fromId: prev.id,
      toId: here.id,
      moving: true,
    }
  }
  return { x: here.x_cm, y: here.y_cm, heading: here.heading ?? 0, fromId: here.id, toId: here.id, moving: false }
}
