import { useState } from 'react'
import Panel from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot, TableGeometry } from '../../types/operations'
import SandTableFigure from './SandTableFigure'
import { roverFix } from './navigation'
import { panelState, sampledCount } from './format'

export default function TestbedOverview({
  snapshot,
  geometry,
  error,
  showBoxes,
  onOpen,
}: {
  snapshot: OperationsSnapshot | null
  geometry: TableGeometry | null
  error: string
  showBoxes: boolean
  onOpen: OpenDialog
}) {
  const [selectedId, setSelectedId] = useState('')
  const sampled = sampledCount(snapshot)
  const plan = snapshot?.search_plan
  const rover = geometry ? roverFix(geometry, snapshot) : null
  const total = snapshot?.scan_route?.length || geometry?.measurement_points.length || 0
  const pose = rover
    ? rover.moving ? `rover moving toward ${rover.toId}` : `rover at ${rover.fromId}`
    : plan
      ? `virtual line · ${plan.path.length} cells · look ${plan.look}`
      : 'rover pose unavailable'
  const cover = geometry ? `${geometry.sand.thick.cover_above_lids_cm} cm nominal cover` : 'cover not loaded'
  const summary = `${cover} · ${sampled}/${total} grid squares · ${pose}`

  return (
    <Panel
      className="map-panel"
      testId="map-panel"
      title="Measured sand table"
      state={panelState(snapshot?.mode)}
      expandLabel="sand table"
      onExpand={() => onOpen({ kind: 'map' })}
    >
      {error ? <p className="quiet-line">{error}</p> : null}
      {!error && !geometry ? <p className="quiet-line">Loading table geometry…</p> : null}
      <p className="intensity-key" aria-label="Four signal intensities">
        <span><i className="swatch" style={{ background: '#c83a3a' }} /> Strong</span>
        <span><i className="swatch" style={{ background: '#b7791f' }} /> Moderate</span>
        <span><i className="swatch" style={{ background: '#16845d' }} /> Quiet</span>
        <span><i className="swatch" style={{ background: '#8b98a8' }} /> Not sampled</span>
      </p>
      {geometry ? (
        <div className="map-frame" title={summary}>
          <SandTableFigure
            geometry={geometry}
            snapshot={snapshot}
            showBoxes={showBoxes}
            selectedId={selectedId}
            onSelect={(pointId) => {
              setSelectedId(pointId)
              onOpen({ kind: 'map', pointId })
            }}
          />
        </div>
      ) : null}
    </Panel>
  )
}
