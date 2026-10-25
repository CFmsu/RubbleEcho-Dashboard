import { useState } from 'react'
import Panel from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot, TableGeometry } from '../../types/operations'
import PointIndex from './PointIndex'
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
  const rover = geometry && !plan ? roverFix(geometry, snapshot) : null
  const pose = plan
    ? `virtual line · ${plan.path.length} cells left · look ${plan.look}`
    : rover
      ? rover.moving ? `rover moving toward ${rover.toId}` : `rover at ${rover.fromId}`
      : 'rover pose unavailable'
  const cover = geometry ? `${geometry.sand.thick.cover_above_lids_cm} cm nominal cover` : 'cover not loaded'
  const summary = `${cover} · ${sampled}/6 sampled points · ${pose}`

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
      {geometry ? (
        <div className="map-frame">
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
          <p className="map-summary" title={summary}>{summary}</p>
          <PointIndex geometry={geometry} snapshot={snapshot} selectedId={selectedId} onSelect={(pointId) => {
            setSelectedId(pointId)
            onOpen({ kind: 'map', pointId })
          }} />
        </div>
      ) : null}
    </Panel>
  )
}
