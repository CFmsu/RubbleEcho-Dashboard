import type { OperationsSnapshot, TableGeometry } from '../../types/operations'
import { gridCells, heatColor, heatLabel, siteInCell } from './navigation'

export default function PointIndex({
  geometry,
  snapshot,
  selectedId,
  caption,
  onSelect,
}: {
  geometry: TableGeometry
  snapshot: OperationsSnapshot | null
  selectedId?: string
  caption?: string
  onSelect?: (pointId: string) => void
}) {
  return (
    <div className="index-wrap">
      {caption ? <p className="map-summary" title={caption}>{caption}</p> : null}
      <p className="legend-line">
        <span><i className="swatch" style={{ background: '#c83a3a' }} /> Strong case</span>
        <span><i className="swatch" style={{ background: '#b7791f' }} /> Moderate</span>
        <span><i className="swatch" style={{ background: '#16845d' }} /> Quiet control</span>
        <span><i className="swatch" style={{ background: '#8b98a8' }} /> Not sampled</span>
      </p>
      <table className="index-table">
        <thead>
          <tr>
            <th>Cell</th>
            <th>Site</th>
            <th>Border</th>
            <th>Reading</th>
          </tr>
        </thead>
        <tbody>
          {gridCells(geometry).map((cell) => {
            const site = siteInCell(geometry, cell.row, cell.col)
            const heat = snapshot?.heatmap_points.find((item) => item.point_id === (site ?? cell.id))
            const score = heat && heat.sample_count > 0 ? heat.score : null
            const label = site ?? cell.id
            return (
              <tr key={cell.id} onClick={() => onSelect?.(label)} style={{ cursor: onSelect ? 'pointer' : undefined }}>
                <td>
                  <span className="swatch" style={{ background: heatColor(score) }} />
                  {selectedId === label ? `${cell.visit} · selected` : cell.visit}
                </td>
                <td>{site ?? '—'}</td>
                <td>{cell.border.toFixed(1)} cm</td>
                <td>{heatLabel(score)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
