import { useState } from 'react'
import DetailDialog, { FactGrid } from './DetailDialog'
import SandTableFigure from '../live/SandTableFigure'
import { readOperatorToken } from '../../api/operations'
import type { OperationsSnapshot, TableGeometry } from '../../types/operations'
import { panelState, pointDetail, sampledCount } from '../live/format'

export default function MapDetailDialog({
  open,
  onClose,
  snapshot,
  geometry,
  showBoxes,
  onShowBoxes,
  pointId = '',
}: {
  open: boolean
  onClose: () => void
  snapshot: OperationsSnapshot | null
  geometry: TableGeometry | null
  showBoxes: boolean
  onShowBoxes: (value: boolean) => void
  pointId?: string
}) {
  const [selectedId, setSelectedId] = useState(pointId)
  const selected = snapshot?.heatmap_points.find((point) => point.point_id === selectedId)
  const canReveal = readOperatorToken().length > 0

  return (
    <DetailDialog open={open} onClose={onClose} title="Measured sand table" state={panelState(snapshot?.mode)}>
      {geometry ? (
        <div className="dialog-map">
          <SandTableFigure geometry={geometry} snapshot={snapshot} showBoxes={showBoxes} selectedId={selectedId} onSelect={setSelectedId} />
        </div>
      ) : <p>Table geometry is unavailable.</p>}
      <p className="quiet-line">{sampledCount(snapshot)}/6 sampled points · {snapshot?.pose?.valid ? 'rover pose valid' : 'rover pose unavailable'} · ground truth {showBoxes ? 'outlines shown' : 'hidden'}</p>
      <label className="check-line">
        <input
          type="checkbox"
          checked={showBoxes}
          disabled={!canReveal}
          onChange={(event) => onShowBoxes(event.target.checked)}
        />
        Show buried box outlines. This does not name which box is the source.
      </label>
      {!canReveal ? <p className="quiet-line">Set the operator token in Diagnostics before showing box outlines.</p> : null}
      <FactGrid
        rows={[
          ['Revision', geometry?.geometry_revision ?? '—'],
          ['Outer', geometry ? `${geometry.outer_cm.width} × ${geometry.outer_cm.height} cm` : '—'],
          ['Inner', geometry ? `${geometry.inner_cm.width} × ${geometry.inner_cm.height} cm` : '—'],
          ['Nominal thick cover', geometry ? `${geometry.sand.thick.cover_above_lids_cm} cm` : '—'],
          ['Nominal thin cover', geometry ? `${geometry.sand.thin.cover_above_lids_cm} cm` : '—'],
          ['Selected point', selected ? pointDetail(selected) : 'Select a marker'],
          ['Pose', snapshot?.pose?.valid ? `${snapshot.pose.x_cm} cm, ${snapshot.pose.y_cm} cm · ${snapshot.pose.source}` : 'unavailable'],
          ['Calibration', snapshot?.calibration.reason ?? 'no calibration'],
        ]}
      />
      <h3 className="dialog-subhead">Measurement points</h3>
      <ul className="plain-list">
        {(geometry?.measurement_points ?? []).map((point) => {
          const heat = snapshot?.heatmap_points.find((item) => item.point_id === point.id)
          return <li key={point.id}>{point.id}: {point.x_cm}, {point.y_cm} cm · {heat ? pointDetail(heat) : 'no samples'}</li>
        })}
      </ul>
      <p className="quiet-line">Scores are an uncalibrated observation heuristic. Unmeasured area stays neutral. Interpolation is not drawn on this map.</p>
    </DetailDialog>
  )
}
