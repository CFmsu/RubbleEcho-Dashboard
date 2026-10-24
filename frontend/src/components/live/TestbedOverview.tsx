import { useState } from 'react'
import Panel from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot, TableGeometry } from '../../types/operations'
import SandTableFigure from './SandTableFigure'
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
  const pose = snapshot?.pose?.valid ? 'rover pose valid' : 'rover pose unavailable'
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
        </div>
      ) : null}
    </Panel>
  )
}
