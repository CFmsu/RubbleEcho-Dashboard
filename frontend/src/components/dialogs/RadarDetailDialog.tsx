import type { OperationsSnapshot } from '../../types/operations'
import { clockLabel, panelState } from '../live/format'
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
      <div className={`scope-stage scope-stage-large ${paused ? 'is-paused' : ''}`} aria-hidden="true">
        <div className="scope-disc" />
        <div className="scope-ring ring-a" />
        <div className="scope-ring ring-b" />
        <div className="scope-ring ring-c" />
        <div className="scope-pivot"><div className="scope-beam" /></div>
      </div>
      <p className="quiet-line">The sweep is an illustration. It is not a rotating antenna and it is not a bearing.</p>
      <FactGrid
        rows={[
          ['Presence', text(radar?.human_presence)],
          ['Distance', radar?.distance_m == null ? '—' : `${radar.distance_m} m`],
          ['Breathing', radar?.breath_rate_bpm == null ? '—' : `${radar.breath_rate_bpm} breaths/min`],
          ['Heart rate', radar?.heart_rate_bpm == null ? '—' : `${radar.heart_rate_bpm} bpm`],
          ['Phase', radar?.total_phase == null ? '—' : `${radar.total_phase} raw`],
          ['Stability', radar?.stability ?? '—'],
          ['Valid', radar ? String(radar.valid) : '—'],
          ['Stale', radar ? String(radar.stale) : '—'],
          ['Firmware', radar?.firmware ?? '—'],
          ['Last sample', clockLabel(radar?.captured_at_utc)],
          ['Source', radar?.source_mode ?? 'unavailable'],
          ['Spatial target', radar?.spatial_coordinates_used && radar.target_xy_m ? radar.target_xy_m.join(', ') + ' m' : 'not plotted'],
        ]}
      />
      <p className="quiet-line">Green means the illustration is active or the sample is unflagged. Amber is an unconfirmed presence report. Gray means disconnected or stale. No polar blip is drawn, because this firmware path does not provide a calibrated angle. Through-sand vital signs are not validated.</p>
      {radar?.notes?.length ? <p className="quiet-line">{radar.notes.join(' · ')}</p> : null}
    </DetailDialog>
  )
}
