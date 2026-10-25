import Panel from '../layout/Panel'
import RadarScope from './RadarScope'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import { panelState } from './format'

export function radarRunning(snapshot: OperationsSnapshot | null): boolean {
  if (snapshot?.run_active) return true
  const radarMode = snapshot?.radar?.source_mode
  if (radarMode === 'live' || radarMode === 'simulation' || radarMode === 'replay') return true
  const device = snapshot?.devices?.find((item) => item.device_id === 'mr60bha2')
  return device?.source_mode === 'live' || device?.source_mode === 'simulation'
}

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
  const paused = !running && (!radar || radar.stale || radar.source_mode === 'unavailable')
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
          running={radarRunning(snapshot)}
        />
      </div>
      <p className="scope-readout" title={line}>{line}</p>
    </Panel>
  )
}
