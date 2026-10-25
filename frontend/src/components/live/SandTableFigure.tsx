import { useEffect, useId, useRef, useState } from 'react'
import type { OperationsSnapshot, TableGeometry } from '../../types/operations'
import { heatColor, roverFix } from './navigation'

const GRID_SPACING_CM = 10

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
  const clipId = `grid-${useId().replace(/:/g, '')}`
  const elapsed = useRunElapsed(snapshot)
  const width = geometry.outer_cm.width
  const height = geometry.outer_cm.height
  const inner = geometry.inner_cm
  const scores = new Map(snapshot?.heatmap_points.map((point) => [point.point_id, point]) ?? [])
  const plan = snapshot?.search_plan
  const cells = new Map(plan?.cells.map((cell) => [cell.point_id, cell]) ?? [])
  const route = geometry.measurement_points
  const rover = plan ? null : roverFix(geometry, snapshot, elapsed)
  const planPath = (plan?.path ?? [])
    .map((pointId) => route.find((point) => point.id === pointId))
    .filter((point): point is (typeof route)[number] => Boolean(point))
    .map((point) => `${point.x_cm},${point.y_cm}`)
    .join(' ')
  const traveled = rover
    ? route
        .filter((point) => {
          const index = route.findIndex((item) => item.id === point.id)
          const current = route.findIndex((item) => item.id === rover.fromId)
          return index <= current
        })
        .map((point) => `${point.x_cm},${point.y_cm}`)
        .concat(`${rover.x},${rover.y}`)
        .join(' ')
    : ''

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Sand table plan, 105 by 80 centimeters" preserveAspectRatio="xMidYMid meet">
      <rect x="0" y="0" width={width} height={height} fill="#fbfcfe" stroke="#17243b" strokeWidth="0.7" />
      <clipPath id={clipId}>
        <rect x={inner.origin_x_cm} y={inner.origin_y_cm} width={inner.width} height={inner.height} />
      </clipPath>
      <g clipPath={`url(#${clipId})`}>
        {Array.from({ length: Math.floor(width / GRID_SPACING_CM) + 1 }, (_, index) => (
          <line key={`x-${index}`} x1={index * GRID_SPACING_CM} y1={0} x2={index * GRID_SPACING_CM} y2={height} stroke="#d5deea" strokeWidth="0.28" />
        ))}
        {Array.from({ length: Math.floor(height / GRID_SPACING_CM) + 1 }, (_, index) => (
          <line key={`y-${index}`} x1={0} y1={index * GRID_SPACING_CM} x2={width} y2={index * GRID_SPACING_CM} stroke="#d5deea" strokeWidth="0.28" />
        ))}
      </g>
      {Array.from({ length: Math.floor(inner.width / 20) + 1 }, (_, index) => {
        const x = inner.origin_x_cm + index * 20
        return <text key={`lx-${index}`} x={x + 0.4} y={inner.origin_y_cm + 2.4} fontSize="1.8" fill="#64748b">{Math.round(x)}</text>
      })}
      {Array.from({ length: Math.floor(inner.height / 20) + 1 }, (_, index) => {
        const y = inner.origin_y_cm + index * 20
        return <text key={`ly-${index}`} x={inner.origin_x_cm + 0.5} y={y - 0.4} fontSize="1.8" fill="#64748b">{Math.round(y)}</text>
      })}
      <rect
        x={inner.origin_x_cm}
        y={inner.origin_y_cm}
        width={inner.width}
        height={inner.height}
        fill="none"
        stroke="#2563eb"
        strokeDasharray="1.4 0.8"
        strokeWidth="0.35"
      />
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
      {planPath ? <polyline points={planPath} fill="none" stroke="#0f766e" strokeWidth="0.55" /> : null}
      {traveled ? <polyline points={traveled} fill="none" stroke="#2563eb" strokeWidth="0.55" /> : null}
      {geometry.measurement_points.map((point) => {
        const heat = scores.get(point.id)
        const sampled = Boolean(heat && heat.sample_count > 0)
        return (
          <g key={point.id} onClick={() => onSelect(point.id)} style={{ cursor: 'pointer' }}>
            <title>{`${point.id} ${point.x_cm} cm, ${point.y_cm} cm`}</title>
            <circle
              cx={point.x_cm}
              cy={point.y_cm}
              r={selectedId === point.id ? 2.4 : sampled ? 1.8 : 1.15}
              fill={cells.get(point.id)?.state === 'blocked' ? '#7f1d1d' : sampled ? heatColor(heat?.score ?? null) : '#c5ced8'}
              stroke={cells.get(point.id)?.state === 'blocked' ? '#fecaca' : '#ffffff'}
              strokeWidth="0.35"
            />
            <text x={point.x_cm + 2.2} y={point.y_cm + 0.8} fontSize="2.1" fill="#334155">{point.id}</text>
          </g>
        )
      })}
      {rover ? (
        <g>
          <g transform={`translate(${rover.x} ${rover.y}) rotate(${rover.heading})`}>
            <polygon points="3.1,0 -1.7,1.35 -1.1,0 -1.7,-1.35" fill="#1d4ed8" stroke="#ffffff" strokeWidth="0.25" />
          </g>
          {rover.moving ? (
            <text x={rover.x + 2.6} y={rover.y - 2.4} fontSize="2.2" fill="#1d4ed8">{`to ${rover.toId}`}</text>
          ) : null}
        </g>
      ) : null}
    </svg>
  )
}

function useRunElapsed(snapshot: OperationsSnapshot | null): number {
  const base = snapshot?.run_elapsed_s ?? 0
  const active = Boolean(snapshot?.run_active)
  const stamp = useRef({ base, at: performance.now() })
  const [elapsed, setElapsed] = useState(base)

  useEffect(() => {
    stamp.current = { base, at: performance.now() }
    setElapsed(base)
  }, [base, active])

  useEffect(() => {
    if (!active) return
    let frame = 0
    const loop = () => {
      setElapsed(stamp.current.base + (performance.now() - stamp.current.at) / 1000)
      frame = requestAnimationFrame(loop)
    }
    frame = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(frame)
  }, [active])

  return elapsed
}
