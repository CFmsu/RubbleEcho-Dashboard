import { useState, type ReactNode } from 'react'
import { FactGrid } from '../../components/dialogs/DetailDialog'
import EchoDiagram from '../../components/live/EchoDiagram'
import PointIndex from '../../components/live/PointIndex'
import RadarScope from '../../components/live/RadarScope'
import { radarRunning } from '../../components/live/RadarOverview'
import SignalScope from '../../components/live/SignalScope'
import { clockLabel } from '../../components/live/format'
import { useGeometry } from '../../hooks/useGeometry'
import type { OperationsSnapshot } from '../../types/operations'

function text(value: number | boolean | null | undefined, suffix = ''): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return `${value}${suffix}`
}

export default function SensorsPage({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const { geometry } = useGeometry()
  const radar = snapshot?.radar
  const range = snapshot?.ultrasonic
  const acoustic = snapshot?.acoustic
  const piezo = snapshot?.piezo
  const trace = snapshot?.rover_trace
  const camera = snapshot?.cameras?.[0]

  return (
    <div className="reading-deck">
      <h2 className="text-xl font-semibold">Live readings</h2>
      <p className="quiet-line">Each card opens the same detail that used to sit in a popup. The live page keeps the waveforms.</p>
      <Reading
        title="Measured sand table"
        headline={geometry ? `${geometry.outer_cm.width} × ${geometry.outer_cm.height} cm` : 'Geometry loading'}
      >
        {geometry ? <PointIndex geometry={geometry} snapshot={snapshot} /> : <p className="quiet-line">Table geometry is unavailable.</p>}
      </Reading>
      <Reading title="Camera" headline={camera?.state ?? 'disconnected'}>
        <div className="preview preview-detail">
          <span className="preview-frame">
            {camera?.image_url ? <img src={camera.image_url} alt="Camera sample" /> : <span className="preview-copy">No stream</span>}
          </span>
        </div>
        <FactGrid rows={[
          ['State', camera?.state ?? 'disconnected'],
          ['Source', camera?.source_mode ?? 'unavailable'],
          ['Frame', clockLabel(camera?.last_frame_utc)],
          ['Size', camera?.width && camera?.height ? `${camera.width} × ${camera.height}` : '—'],
        ]} />
      </Reading>
      <Reading
        title="60 GHz radar"
        headline={radar?.distance_m == null ? 'No range' : `${radar.distance_m} m · ${text(radar.human_presence)} presence`}
      >
        <div className="scope-stage" style={{ height: 280 }}>
          <RadarScope
            distanceM={radar?.distance_m}
            presence={radar?.human_presence}
            targets={radar?.num_targets}
            breath={radar?.breath_rate_bpm}
            heart={radar?.heart_rate_bpm}
            running={radarRunning(snapshot)}
          />
        </div>
        <FactGrid rows={[
          ['Presence', text(radar?.human_presence)],
          ['Distance', radar?.distance_m == null ? '—' : `${radar.distance_m} m`],
          ['Breathing', radar?.breath_rate_bpm == null ? '—' : `${radar.breath_rate_bpm} breaths/min`],
          ['Heart rate', radar?.heart_rate_bpm == null ? '—' : `${radar.heart_rate_bpm} bpm`],
          ['Targets', radar?.num_targets == null ? '—' : String(radar.num_targets)],
          ['Breath phase', text(radar?.breath_phase)],
          ['Heart phase', text(radar?.heart_phase)],
          ['Source', radar?.source_mode ?? 'unavailable'],
          ['Bearing', 'not reported by this module'],
          ['Last sample', clockLabel(radar?.captured_at_utc)],
        ]} />
      </Reading>
      <Reading title="Ultrasonic" headline={range?.distance_cm == null ? 'No echo' : `${range.distance_cm} cm`}>
        <EchoDiagram distanceCm={range?.distance_cm ?? null} echoTimeout={Boolean(range?.echo_timeout)} />
        <FactGrid rows={[
          ['Direction', range?.direction ?? '—'],
          ['Quality', range?.quality ?? 'no sample'],
          ['Echo timeout', range ? (range.echo_timeout ? 'yes' : 'no') : '—'],
          ['Source', range?.source_mode ?? 'unavailable'],
          ['Meaning', 'Obstacle range in front of the sensor. Not depth through rubble.'],
        ]} />
      </Reading>
      <Reading title="Acoustic" headline={acoustic?.class ?? 'No samples'}>
        <SignalScope samples={snapshot?.acoustic_waveform ?? []} label="Acoustic waveform" large />
        <FactGrid rows={[
          ['Class', acoustic?.class ?? 'No samples'],
          ['Level', acoustic?.rms_dbfs == null ? '—' : `${acoustic.rms_dbfs} dBFS`],
          ['Site', acoustic?.site_id ?? '—'],
          ['Source', acoustic?.source_mode ?? 'unavailable'],
          ['Channels', acoustic?.channel_note ?? 'Not enumerated.'],
        ]} />
      </Reading>
      <Reading title="Vibration" headline={piezo ? `${piezo.peak_adc_counts} counts` : 'No contact sample'}>
        <SignalScope samples={snapshot?.piezo_waveform ?? []} label="Piezo waveform" color="#b45309" large />
        <FactGrid rows={[
          ['Peak', piezo ? `${piezo.peak_adc_counts} ${piezo.unit}` : '—'],
          ['RMS', piezo ? `${piezo.rms_adc_counts} ${piezo.unit}` : '—'],
          ['Contact', piezo?.contact_state ?? 'No contact sample'],
          ['Site', piezo?.site_id ?? '—'],
          ['Clipped', piezo ? (piezo.clipped ? 'yes' : 'no') : '—'],
          ['Acceleration', 'not measured'],
        ]} />
      </Reading>
      <Reading title="Rover" headline={trace ? `L ${trace.left_counts} · R ${trace.right_counts}` : 'Encoders quiet'}>
        <SignalScope samples={trace?.left ?? []} secondary={trace?.right ?? []} label="Encoder ticks" large />
        <FactGrid rows={[
          ['Left', trace ? String(trace.left_counts) : '—'],
          ['Right', trace ? String(trace.right_counts) : '—'],
          ['Heading', snapshot?.pose?.heading_deg == null ? '—' : `${snapshot.pose.heading_deg}°`],
          ['Pose', snapshot?.pose?.valid ? `${snapshot.pose.x_cm} cm, ${snapshot.pose.y_cm} cm` : 'unavailable'],
          ['Knock', snapshot?.solenoid.state ?? 'DISARMED'],
          ['Pin', snapshot?.solenoid.note ?? 'A0'],
        ]} />
      </Reading>
    </div>
  )
}

function Reading({
  title,
  headline,
  children,
}: {
  title: string
  headline: string
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)
  return (
    <article className="reading-card">
      <button type="button" className="reading-head" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
        <strong>{title}</strong>
        <span>{headline}</span>
        <em>{open ? 'Hide detail' : 'Expand'}</em>
      </button>
      {open ? <div className="reading-body">{children}</div> : null}
    </article>
  )
}
