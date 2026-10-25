import type { OperationsSnapshot, TableGeometry } from '../../types/operations'
import { heatColor, heatLabel } from './navigation'

export default function PointIndex({
  geometry,
  snapshot,
  selectedId,
  onSelect,
}: {
  geometry: TableGeometry
  snapshot: OperationsSnapshot | null
  selectedId?: string
  onSelect?: (pointId: string) => void
}) {
  return (
    <div className="index-wrap">
      <p className="legend-line">
        <span><i className="swatch" style={{ background: '#c83a3a' }} /> Strong case</span>
        <span><i className="swatch" style={{ background: '#b7791f' }} /> Moderate</span>
        <span><i className="swatch" style={{ background: '#16845d' }} /> Quiet control</span>
        <span><i className="swatch" style={{ background: '#8b98a8' }} /> Not sampled</span>
      </p>
      <table className="index-table">
        <thead>
          <tr>
            <th>Point</th>
            <th>X cm</th>
            <th>Y cm</th>
            <th>Index</th>
          </tr>
        </thead>
        <tbody>
          {geometry.measurement_points.map((point) => {
            const heat = snapshot?.heatmap_points.find((item) => item.point_id === point.id)
            const score = heat && heat.sample_count > 0 ? heat.score : null
            return (
              <tr key={point.id} onClick={() => onSelect?.(point.id)} style={{ cursor: onSelect ? 'pointer' : undefined }}>
                <td>
                  <span className="swatch" style={{ background: heatColor(score) }} />
                  {selectedId === point.id ? `${point.id} · selected` : point.id}
                </td>
                <td>{point.x_cm.toFixed(1)}</td>
                <td>{point.y_cm.toFixed(1)}</td>
                <td>{heatLabel(score)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
