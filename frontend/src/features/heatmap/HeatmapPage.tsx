import SandTableMap from '../operations/SandTableMap'
import type { OperationsSnapshot } from '../../types/operations'

export default function HeatmapPage({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const points = snapshot?.heatmap_points ?? []
  return (
    <div className="space-y-4">
      <SandTableMap snapshot={snapshot} />
      <section className="ops-card">
        <h2 className="text-xl font-semibold">Measured points</h2>
        <p className="mt-2 text-sm text-slate-600">Scores are an uncalibrated observation heuristic. Unmeasured locations are omitted. Interpolation is not shown on this map.</p>
        {points.length === 0 ? <p className="mt-3 text-sm">No measured points in the current view.</p> : null}
        <ul className="mt-3 space-y-2 text-sm">
          {points.map((point) => (
            <li key={point.point_id}>
              {point.point_id}: {point.score} ({point.score_semantics}) · {point.source_mode} · samples {point.sample_count}
              {point.interpolated ? ' · interpolated' : ' · measured'}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
