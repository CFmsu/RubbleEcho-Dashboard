import Panel from '../layout/Panel'
import RadarScope from './RadarScope'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import { panelState } from './format'
import { radarRunning } from './radarFeed'

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
  const running = Boolean(snapshot?.run_active)
  const liveFeed = radarRunning(snapshot)
  const paused = !liveFeed && (!radar || radar.stale || radar.source_mode === 'unavailable')
  const state = running ? 'SIMULATION' : panelState(radar?.source_mode, Boolean(radar?.stale))
  const presence = radar ? reading(radar.human_presence) : '—'
  const distance = radar?.distance_m == null ? '—' : `${radar.distance_m} m`
  const breath = radar?.breath_rate_bpm == null ? null : `${radar.breath_rate_bpm} breaths/min`
  const heart = radar?.heart_rate_bpm == null ? null : `${radar.heart_rate_bpm} bpm`
  const targets = radar?.num_targets == null ? null : `${radar.num_targets} target${radar.num_targets === 1 ? '' : 's'}`
  const vital = [breath, heart, targets].filter(Boolean).join(' · ')
  const line = radar?.case_name
    ? `${radar.case_name} · Presence ${presence} · ${distance}${vital ? ` · ${vital}` : ''}`
    : running
      ? 'Simulation timing only. No target.'
      : paused && !radar
        ? 'No radar data'
        : `Presence ${presence} · ${distance}${vital ? ` · ${vital}` : ''}`
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
          breath={radar?.breath_rate_bpm}
          heart={radar?.heart_rate_bpm}
          running={liveFeed}
        />
      </div>
      <p className="scope-readout" title={line}>{line}</p>
    </Panel>
  )
}
