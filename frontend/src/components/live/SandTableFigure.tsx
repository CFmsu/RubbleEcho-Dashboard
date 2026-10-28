import { useEffect, useRef, useState } from 'react'
import type { OperationsSnapshot, TableGeometry } from '../../types/operations'
import { driveRoute, echoFix, gridCells, heatColor, roverFix, siteInCell } from './navigation'

export default function SandTableFigure({
  geometry,
  snapshot,
  showBoxes,
  selectedId,
  onSelect,
}: {
  geometry: TableGeometry
  snapshot: OperationsSnapshot | null
  showBoxes: boolean
  selectedId: string
  onSelect: (pointId: string) => void
}) {
  const elapsed = useRunElapsed(snapshot)
  const legElapsed = useLegElapsed(snapshot?.rover_leg)
  const width = geometry.outer_cm.width
  const height = geometry.outer_cm.height
  const scores = new Map(snapshot?.heatmap_points.map((point) => [point.point_id, point]) ?? [])
  const plan = snapshot?.search_plan
  const boxes = gridCells(geometry)
  const named = new Map(geometry.measurement_points.map((point) => [point.id, point]))
  const drive = driveRoute(geometry, snapshot)
  const rover = roverFix(geometry, snapshot, elapsed, legElapsed)
  const liveTrack = snapshot?.pose?.source === 'arduino_uno'
  const echo = echoFix(rover, snapshot?.ultrasonic?.distance_cm, Boolean(snapshot?.ultrasonic?.echo_timeout), width, height)
  const planPath = (plan?.path ?? [])
    .map((pointId) => named.get(pointId))
    .filter((point): point is (typeof geometry.measurement_points)[number] => Boolean(point))
    .map((point) => `${point.x_cm},${point.y_cm}`)
    .join(' ')
  const traveled = liveTrack
    ? (snapshot?.pose_trail ?? [])
        .filter((pose) => pose.valid && pose.x_cm != null && pose.y_cm != null)
        .map((pose) => `${pose.x_cm},${pose.y_cm}`)
        .concat(rover ? [`${rover.x},${rover.y}`] : [])
        .join(' ')
    : rover
    ? drive
        .filter((point) => {
          const index = drive.findIndex((item) => item.id === point.id)
          const current = drive.findIndex((item) => item.id === rover.fromId)
          return index <= current
        })
        .map((point) => `${point.x_cm},${point.y_cm}`)
        .concat(`${rover.x},${rover.y}`)
        .join(' ')
    : ''

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Sand table plan, 105 by 80 centimeters" preserveAspectRatio="xMidYMid meet">
      <rect x="0" y="0" width={width} height={height} fill="#fbfcfe" stroke="#17243b" strokeWidth="0.7" />
      {boxes.map((cell) => {
        const site = siteInCell(geometry, cell.row, cell.col)
        const heat = scores.get(site ?? '') ?? scores.get(cell.id)
        const sampled = Boolean(heat && heat.sample_count > 0)
        const stoppedHere = rover != null && !rover.moving && rover.fromId === cell.id
        const selected = selectedId === cell.id || selectedId === site
        return (
          <g key={cell.id} onClick={() => onSelect(site ?? cell.id)} style={{ cursor: 'pointer' }}>
            <title>{`${cell.id}${site ? ` · ${site}` : ''} · border ${cell.border} cm`}</title>
            <rect
              x={cell.originX}
              y={cell.originY}
              width={cell.width}
              height={cell.height}
              fill={sampled ? heatColor(heat?.score ?? null) : stoppedHere ? '#dbeafe' : '#f4f7fb'}
              fillOpacity={sampled ? 0.82 : 1}
              stroke={stoppedHere || selected ? '#1d4ed8' : '#64748b'}
              strokeWidth={stoppedHere || selected ? 0.7 : 0.4}
            />
            <text x={cell.originX + 1.2} y={cell.originY + 3.4} fontSize="2.6" fill="#334155">{cell.visit}</text>
            <text x={cell.x_cm} y={cell.y_cm - 1.6} textAnchor="middle" fontSize="2.4" fill="#17243b">{site ?? cell.id}</text>
          </g>
        )
      })}
      {showBoxes
        ? geometry.boxes.map((box) => (
            <g key={box.id}>
              <rect
                x={box.center_cm.x - box.plan_width_cm / 2}
                y={box.center_cm.y - box.plan_height_cm / 2}
                width={box.plan_width_cm}
                height={box.plan_height_cm}
                fill="#ffffff"
                stroke="#334155"
                strokeWidth="0.4"
              />
              <text x={box.center_cm.x} y={box.center_cm.y} textAnchor="middle" fontSize="3" fill="#17243b">{box.id}</text>
            </g>
          ))
        : null}
      {plan?.boundary.map((line, index) => (
        <line
          key={`bound-${index}`}
          x1={line.x1_cm}
          y1={line.y1_cm}
          x2={line.x2_cm}
          y2={line.y2_cm}
          stroke="#b45309"
          strokeWidth="0.7"
        />
      ))}
      {planPath && !snapshot?.scan_route?.length ? <polyline points={planPath} fill="none" stroke="#0f766e" strokeWidth="0.55" /> : null}
      {traveled ? <polyline points={traveled} fill="none" stroke="#2563eb" strokeWidth="0.55" /> : null}
      {rover && !rover.moving && echo ? (
        <g>
          <line x1={rover.x} y1={rover.y} x2={echo.x} y2={echo.y} stroke="#7c3aed" strokeWidth="0.28" strokeDasharray="0.7 0.45" />
          <circle cx={echo.x} cy={echo.y} r="1.35" fill="#ddd6fe" stroke="#7c3aed" strokeWidth="0.35">
            <title>{`Ultrasonic return ${snapshot?.ultrasonic?.distance_cm} cm`}</title>
          </circle>
        </g>
      ) : null}
      {rover ? (
        <g>
          <g transform={`translate(${rover.x} ${rover.y}) rotate(${rover.heading})`}>
            <polygon points="3.1,0 -1.7,1.35 -1.1,0 -1.7,-1.35" fill="#1d4ed8" stroke="#ffffff" strokeWidth="0.25" />
          </g>
          <text x={rover.x + 2.6} y={rover.y - 2.4} fontSize="2.2" fill="#1d4ed8">
            {rover.moving ? `to ${rover.toId}` : liveTrack ? rover.fromId : snapshot?.mission_phase === 'SIGNS' ? 'signs' : snapshot?.mission_phase === 'VITALS' ? 'vitals' : snapshot?.mission_phase === 'TURN' ? 'turn' : ''}
          </text>
        </g>
      ) : null}
    </svg>
  )
}

function useRunElapsed(snapshot: OperationsSnapshot | null): number {
  const base = snapshot?.run_elapsed_s ?? 0
  const active = Boolean(snapshot?.run_active)
  const stamp = useRef<{ base: number; at: number } | null>(null)
  const [elapsed, setElapsed] = useState(base)
  const [clock, setClock] = useState({ base, active })
  if (clock.base !== base || clock.active !== active) {
    setClock({ base, active })
    setElapsed(base)
  }

  useEffect(() => {
    if (!active) return
    stamp.current = { base, at: performance.now() }
    let frame = 0
    const loop = () => {
      const mark = stamp.current
      if (!mark) return
      setElapsed(mark.base + (performance.now() - mark.at) / 1000)
      frame = requestAnimationFrame(loop)
    }
    frame = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(frame)
  }, [active, base])

  return elapsed
}

function useLegElapsed(leg: OperationsSnapshot['rover_leg']): number | undefined {
  const key = leg ? `${leg.from_id}:${leg.to_id}:${leg.duration_ms}` : ''
  const mark = leg?.elapsed_ms ?? 0
  const stamp = useRef<{ base: number; at: number } | null>(null)
  const [elapsed, setElapsed] = useState(mark)
  const [seen, setSeen] = useState({ key, mark })
  if (seen.key !== key || seen.mark !== mark) {
    setSeen({ key, mark })
    setElapsed(mark)
  }

  useEffect(() => {
    if (!key) return
    stamp.current = { base: mark, at: performance.now() }
    let frame = 0
    const loop = () => {
      const origin = stamp.current
      if (!origin) return
      setElapsed(origin.base + (performance.now() - origin.at))
      frame = requestAnimationFrame(loop)
    }
    frame = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(frame)
  }, [key, mark])

  return leg ? elapsed : undefined
}
