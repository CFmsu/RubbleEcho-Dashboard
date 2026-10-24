import type { OperationsSnapshot, TableGeometry } from '../../types/operations'

const GRID_SPACING_CM = 10

function heatColor(score: number | null): string {
  if (score === null) return '#8b98a8'
  if (score < 0.3) return '#16845d'
  if (score < 0.6) return '#b7791f'
  return '#c83a3a'
}

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
  const width = geometry.outer_cm.width
  const height = geometry.outer_cm.height
  const scores = new Map(snapshot?.heatmap_points.map((point) => [point.point_id, point]) ?? [])

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Sand table plan, 105 by 80 centimeters" preserveAspectRatio="xMidYMid meet">
      {Array.from({ length: Math.floor(width / GRID_SPACING_CM) + 1 }, (_, index) => (
        <line key={`x-${index}`} x1={index * GRID_SPACING_CM} y1={0} x2={index * GRID_SPACING_CM} y2={height} stroke="#e6ebf2" strokeWidth="0.25" />
      ))}
      {Array.from({ length: Math.floor(height / GRID_SPACING_CM) + 1 }, (_, index) => (
        <line key={`y-${index}`} x1={0} y1={index * GRID_SPACING_CM} x2={width} y2={index * GRID_SPACING_CM} stroke="#e6ebf2" strokeWidth="0.25" />
      ))}
      <rect x="0" y="0" width={width} height={height} fill="#fbfcfe" stroke="#17243b" strokeWidth="0.7" />
      <rect
        x={geometry.inner_cm.origin_x_cm}
        y={geometry.inner_cm.origin_y_cm}
        width={geometry.inner_cm.width}
        height={geometry.inner_cm.height}
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
      {snapshot?.pose_trail.map((pose, index) =>
        pose.valid && pose.x_cm !== null && pose.y_cm !== null ? (
          <circle key={`trail-${index}`} cx={pose.x_cm} cy={pose.y_cm} r="0.6" fill="#93c5fd" />
        ) : null,
      )}
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
              fill={sampled ? heatColor(heat?.score ?? null) : '#c5ced8'}
              stroke="#ffffff"
              strokeWidth="0.35"
            />
            <text x={point.x_cm + 2.2} y={point.y_cm + 0.8} fontSize="2.1" fill="#334155">{point.id}</text>
          </g>
        )
      })}
      {snapshot?.pose?.valid && snapshot.pose.x_cm !== null && snapshot.pose.y_cm !== null ? (
        <circle cx={snapshot.pose.x_cm} cy={snapshot.pose.y_cm} r="1.7" fill="#2563eb" stroke="#ffffff" strokeWidth="0.35" />
      ) : null}
    </svg>
  )
}
