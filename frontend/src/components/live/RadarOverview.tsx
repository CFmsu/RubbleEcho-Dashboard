import Panel from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import { panelState } from './format'

function reading(value: number | boolean | null | undefined, suffix = ''): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return `${value}${suffix}`
}

export default function RadarOverview({
  snapshot,
  onOpen,
}: {
  snapshot: OperationsSnapshot | null
  onOpen: OpenDialog
}) {
  const radar = snapshot?.radar ?? null
  const paused = !radar || radar.stale || radar.source_mode === 'unavailable'
  const state = panelState(radar?.source_mode, Boolean(radar?.stale))
  const presence = radar ? reading(radar.human_presence) : '—'
  const distance = radar?.distance_m == null ? '—' : `${radar.distance_m} m`
  const line = paused && !radar
    ? 'No radar data'
    : `Presence ${presence} · Distance ${distance}`

  return (
    <Panel
      className="radar-panel"
      testId="radar-panel"
      title="60 GHz radar"
      state={state}
      expandLabel="radar"
      onExpand={() => onOpen({ kind: 'radar' })}
    >
      <div className={`scope-stage ${paused ? 'is-paused' : ''}`} aria-hidden="true">
        <div className="scope-disc" />
        <div className="scope-ring ring-a" />
        <div className="scope-ring ring-b" />
        <div className="scope-ring ring-c" />
        <div className="scope-pivot"><div className="scope-beam" /></div>
        {radar?.human_presence === true ? (
          <div className="scope-callout">Presence reported{radar.distance_m == null ? '' : ` · ${radar.distance_m} m`}</div>
        ) : null}
      </div>
      <p className="scope-readout" title={line}>{line}</p>
    </Panel>
  )
}
