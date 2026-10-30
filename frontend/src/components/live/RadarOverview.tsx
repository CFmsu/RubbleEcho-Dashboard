import Panel from '../layout/Panel'
import SensorCountdown from './SensorCountdown'
import RadarScope from './RadarScope'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import { panelState } from './format'
import { radarRunning } from './radarFeed'

export default function RadarOverview({
  snapshot,
  onOpen,
}: {
  snapshot: OperationsSnapshot | null
  onOpen: OpenDialog
}) {
  const radar = snapshot?.radar ?? null
  const running = Boolean(snapshot?.run_active)
  const liveFeed = radarRunning(snapshot)
  const paused = !liveFeed && (!radar || radar.stale || radar.source_mode === 'unavailable')
  const state = radar?.source_mode === 'live'
    ? panelState('live', Boolean(radar.stale))
    : running
      ? 'SIMULATION'
      : panelState(radar?.source_mode, Boolean(radar?.stale))
  const distance = radar?.distance_m == null ? '—' : `${radar.distance_m} m`
  const line = radar?.case_name
    ? `${radar.case_name} · range ${distance}`
    : running
      ? 'Waiting for a range.'
      : paused && !radar
        ? 'No radar data'
        : `Range ${distance}`
  return (
    <Panel
      className="radar-panel"
      testId="radar-panel"
      title="60 GHz radar"
      state={state}
      expandLabel="radar"
      onExpand={() => onOpen({ kind: 'radar' })}
    >
      <div className={`scope-stage ${paused ? 'is-paused' : ''}`}>
        <RadarScope
          distanceM={radar?.distance_m}
          presence={radar?.human_presence}
          targets={radar?.num_targets}
          running={liveFeed}
        />
      </div>
      <SensorCountdown snapshot={snapshot} sensor="radar" />
      <p className="scope-readout" title={line}>{line}</p>
    </Panel>
  )
}
