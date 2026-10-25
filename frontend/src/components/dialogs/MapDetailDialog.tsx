import { useState } from 'react'
import DetailDialog, { FactGrid } from './DetailDialog'
import PointIndex from '../live/PointIndex'
import SandTableFigure from '../live/SandTableFigure'
import { roverFix } from '../live/navigation'
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
      <h3 className="dialog-subhead">Heatmap index</h3>
      <p className="quiet-line">
        {snapshot?.search_plan
          ? `The amber line is the virtual boundary. The teal line is the remaining grid order. Look ${snapshot.search_plan.look}. Motors are not commanded.`
          : geometry && roverFix(geometry, snapshot)
            ? `Simulation marker heading toward ${roverFix(geometry, snapshot)?.toId}.`
            : 'Plan grid draws the virtual boundary. A simulation run can still show its own marker.'}
      </p>
      {geometry ? (
        <PointIndex geometry={geometry} snapshot={snapshot} selectedId={selectedId} onSelect={setSelectedId} />
      ) : null}
      <p className="quiet-line">Scores are an uncalibrated observation heuristic. Unmeasured area stays neutral. Interpolation is not drawn on this map.</p>
    </DetailDialog>
  )
}
