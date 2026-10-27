import { useEffect, useState } from 'react'
import { fetchGeometry } from '../../api/operations'
import type { HeatPoint, OperationsSnapshot, TableGeometry } from '../../types/operations'

const GRID_SPACING_CM = 10

function heatColor(score: number | null): string {
  if (score === null) return '#94a3b8'
  if (score < 0.3) return '#0f766e'
  if (score < 0.6) return '#d97706'
  return '#b91c1c'
}

function isGeometry(value: unknown): value is TableGeometry {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return typeof record.outer_cm === 'object' && Array.isArray(record.boxes) && Array.isArray(record.measurement_points)
}

export default function SandTableMap({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const [geometry, setGeometry] = useState<TableGeometry | null>(null)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<string>('')

  useEffect(() => {
    let active = true
    fetchGeometry()
      .then((payload) => {
        if (!active) return
        if (!isGeometry(payload)) {
          setError('Geometry response was not usable.')
          return
        }
        setGeometry(payload)
      })
      .catch(() => {
        if (active) setError('Table geometry is unavailable.')
      })
    return () => {
      active = false
    }
  }, [])

  if (error) return <section className="ops-card ops-map"><h2 className="text-xl font-semibold">Sand table</h2><p>{error}</p></section>
  if (!geometry) return <section className="ops-card ops-map"><p>Loading sand-table geometry…</p></section>

  const width = geometry.outer_cm.width
  const height = geometry.outer_cm.height
  const points = new Map(snapshot?.heatmap_points.map((point) => [point.point_id, point]) ?? [])
  const selectedPoint = snapshot?.heatmap_points.find((point) => point.point_id === selected)

  return (
    <section className="ops-card ops-map">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-xl font-semibold">Sand table Rev C</h2>
        <p className="text-xs text-slate-500">{geometry.geometry_revision} · {geometry.units}</p>
      </div>
      <p className="mb-3 text-xs text-slate-600">
        Thick cover {geometry.sand.thick.cover_above_lids_cm} cm · thin cover {geometry.sand.thin.cover_above_lids_cm} cm.
        Boxes are evaluation geometry. The active source stays hidden until an operator releases it.
      </p>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Sand table plan in centimeters" className="h-auto w-full rounded-lg bg-slate-50">
        {Array.from({ length: Math.floor(width / GRID_SPACING_CM) + 1 }, (_, index) => (
          <line key={`x-${index}`} x1={index * GRID_SPACING_CM} y1={0} x2={index * GRID_SPACING_CM} y2={height} stroke="#e2e8f0" strokeWidth="0.3" />
        ))}
        {Array.from({ length: Math.floor(height / GRID_SPACING_CM) + 1 }, (_, index) => (
          <line key={`y-${index}`} x1={0} y1={index * GRID_SPACING_CM} x2={width} y2={index * GRID_SPACING_CM} stroke="#e2e8f0" strokeWidth="0.3" />
        ))}
        <rect x="0" y="0" width={width} height={height} fill="none" stroke="#0e1b32" strokeWidth="0.8" />
        <rect
          x={geometry.inner_cm.origin_x_cm}
          y={geometry.inner_cm.origin_y_cm}
          width={geometry.inner_cm.width}
          height={geometry.inner_cm.height}
          fill="none"
          stroke="#2463eb"
          strokeDasharray="1.2 0.8"
          strokeWidth="0.4"
        />
        {geometry.boxes.map((box) => (
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
            <text x={box.center_cm.x} y={box.center_cm.y} textAnchor="middle" fontSize="3.2" fill="#0e1b32">{box.id}</text>
          </g>
        ))}
        {snapshot?.pose_trail.map((pose, index) =>
          pose.valid && pose.x_cm !== null && pose.y_cm !== null ? (
            <circle key={`trail-${index}`} cx={pose.x_cm} cy={pose.y_cm} r="0.7" fill="#93c5fd" />
          ) : null,
        )}
        {(snapshot?.scan_route?.length
          ? snapshot.scan_route.map((cell) => ({ id: cell.id, x_cm: cell.x_cm, y_cm: cell.y_cm }))
          : geometry.measurement_points
        ).map((point) => {
          const heat = points.get(point.id)
          const named = !point.id.startsWith('x')
          return (
            <g key={point.id} onClick={() => setSelected(point.id)} style={{ cursor: 'pointer' }}>
              <circle cx={point.x_cm} cy={point.y_cm} r={heat ? 1.5 : 1.05} fill={heatColor(heat?.score ?? null)} stroke="#ffffff" strokeWidth="0.3" />
              {named ? <text x={point.x_cm + 2.2} y={point.y_cm + 0.8} fontSize="2.1" fill="#334155">{point.id}</text> : null}
            </g>
          )
        })}
        {snapshot?.pose?.valid && snapshot.pose.x_cm !== null && snapshot.pose.y_cm !== null ? (
          <circle cx={snapshot.pose.x_cm} cy={snapshot.pose.y_cm} r="1.6" fill="#2463eb" />
        ) : null}
      </svg>
      <ul className="mt-3 flex flex-wrap gap-3 text-xs text-slate-600">
        <li>Blue = rover pose when a fix exists</li>
        <li>Green = weak measured score</li>
        <li>Yellow = investigate</li>
        <li>Red = high heuristic score, not a confirmed person</li>
        <li>Gray = no samples</li>
      </ul>
      <p className="mt-2 text-xs text-slate-500">{geometry.coupling_note}</p>
      {snapshot?.pose?.valid ? (
        <p className="mt-2 text-xs">Pose source: {snapshot.pose.source}. {snapshot.pose.note ?? 'Footprint is unmeasured, so the marker is not to scale.'}</p>
      ) : (
        <p className="mt-2 text-xs">No rover pose. A marker appears only after a valid fix.</p>
      )}
      {selectedPoint ? <PointDetail point={selectedPoint} /> : null}
    </section>
  )
}

function PointDetail({ point }: { point: HeatPoint }) {
  return (
    <div className="mt-3 rounded-lg bg-slate-50 p-3 text-sm">
      <p className="font-medium">{point.point_id}</p>
      <p>{point.x_cm} cm, {point.y_cm} cm · samples {point.sample_count} · {point.method}</p>
      <p>Score {point.score ?? 'unknown'} ({point.score_semantics}) · {point.source_mode} · {point.interpolated ? 'interpolated' : 'measured'}</p>
      <p>Evidence {point.evidence_event_ids.join(', ') || 'none'}</p>
    </div>
  )
}
