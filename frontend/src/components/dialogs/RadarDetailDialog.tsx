import type { OperationsSnapshot } from '../../types/operations'
import { clockLabel, panelState } from '../live/format'
import { radarRunning } from '../live/radarFeed'
import RadarScope from '../live/RadarScope'
import DetailDialog, { FactGrid } from './DetailDialog'

function text(value: number | boolean | null | undefined, suffix = ''): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return `${value}${suffix}`
}

export default function RadarDetailDialog({
  open,
  snapshot,
  onClose,
}: {
  open: boolean
  snapshot: OperationsSnapshot | null
  onClose: () => void
}) {
  const radar = snapshot?.radar
  const paused = !radar || radar.stale || radar.source_mode === 'unavailable'
  return (
    <DetailDialog open={open} onClose={onClose} title="MR60BHA2" state={panelState(radar?.source_mode, Boolean(radar?.stale))}>
      <div className={`scope-stage scope-stage-large ${paused ? 'is-paused' : ''}`}>
        <RadarScope
          distanceM={radar?.distance_m}
          presence={radar?.human_presence}
          targets={radar?.num_targets}
          running={radarRunning(snapshot)}
        />
      </div>
      <p className="quiet-line">The line turns while a radar process is running, and it stops when that process stops. A dot marks a reported person at the measured range. Ring numbers are centimeters. Illuminance is the kit light sensor.</p>
      <FactGrid
        rows={[
          ['Presence', text(radar?.human_presence)],
          ['Distance', radar?.distance_m == null ? '—' : `${radar.distance_m} m`],
          ['Breathing', radar?.breath_rate_bpm == null ? '—' : `${radar.breath_rate_bpm} breaths/min`],
          ['Heart rate', radar?.heart_rate_bpm == null ? '—' : `${radar.heart_rate_bpm} bpm`],
          ['Targets', radar?.num_targets == null ? '—' : String(radar.num_targets)],
          ['Illuminance', radar?.illuminance_lx == null ? '—' : `${radar.illuminance_lx} lx`],
          ['Breath phase', radar?.breath_phase == null ? '—' : String(radar.breath_phase)],
          ['Heart phase', radar?.heart_phase == null ? '—' : String(radar.heart_phase)],
          ['Phase', radar?.total_phase == null ? '—' : `${radar.total_phase} raw`],
          ['Stability', radar?.stability ?? '—'],
          ['Valid', radar ? String(radar.valid) : '—'],
          ['Stale', radar ? String(radar.stale) : '—'],
          ['Firmware', radar?.firmware ?? '—'],
          ['Last sample', clockLabel(radar?.captured_at_utc)],
          ['Source', radar?.source_mode ?? 'live'],
          ['Case', radar?.case_name ?? '—'],
          ['Bearing', 'not reported by this module'],
          ['Spatial target', radar?.spatial_coordinates_used && radar.target_xy_m ? radar.target_xy_m.join(', ') + ' m' : 'not plotted'],
        ]}
      />
      <p className="quiet-line">Ring numbers are centimeters. Through-sand vital signs are not validated.</p>
      {radar?.notes?.length ? <p className="quiet-line">{radar.notes.join(' · ')}</p> : null}
    </DetailDialog>
  )
}
