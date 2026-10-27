import SignalScope from '../../components/live/SignalScope'
import type { OperationsSnapshot } from '../../types/operations'

export default function SensorCards({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const envelope = snapshot?.impulse_envelope_dbfs?.length
    ? snapshot.impulse_envelope_dbfs
    : snapshot?.acoustic_envelope_dbfs ?? []
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <article className="ops-card">
        <h3 className="font-semibold">HC-SR04 obstacle distance</h3>
        <p className="mt-2 text-3xl font-semibold">{snapshot?.ultrasonic?.distance_cm ?? '—'} <span className="text-base font-normal">cm</span></p>
        <p className="text-xs text-slate-500">Direction {snapshot?.ultrasonic?.direction ?? '—'} · {snapshot?.ultrasonic?.quality ?? 'no sample'} · {snapshot?.ultrasonic?.source_mode ?? 'unavailable'}</p>
        <p className="mt-1 text-xs">This is obstacle range, not depth through rubble. Stop margin default 20 cm, pending a measured rover.</p>
        {snapshot?.ultrasonic?.echo_timeout ? <p className="text-sm text-amber-700">Echo timeout. The path is not clear.</p> : null}
      </article>
      <article className="ops-card">
        <h3 className="font-semibold">ReSpeaker acoustic window</h3>
        <p className="mt-2 text-lg">{snapshot?.acoustic?.class ?? 'no samples'}</p>
        <p className="text-xs text-slate-500">
          {snapshot?.acoustic?.score_semantics ?? 'not scored'} {snapshot?.acoustic?.model_score ?? ''} · origin unknown · {snapshot?.acoustic?.source_mode ?? 'unavailable'}
        </p>
        <SignalScope samples={snapshot?.acoustic_waveform ?? []} label="Acoustic waveform" large />
        <Waveform values={envelope} />
        <p className="mt-1 text-xs text-slate-500">{snapshot?.acoustic_envelope_note ?? 'No envelope.'}</p>
        {snapshot?.impulse ? <p className="text-xs">Strongest impulse in this trial: {snapshot.impulse.class} at {snapshot.impulse.site_id ?? 'unknown site'}.</p> : null}
      </article>
      <article className="ops-card">
        <h3 className="font-semibold">Piezo contact vibration</h3>
        <p className="mt-2 text-3xl font-semibold">{snapshot?.piezo?.peak_adc_counts ?? '—'} <span className="text-base">counts</span></p>
        <p className="text-xs text-slate-500">{snapshot?.piezo?.contact_state ?? 'no contact sample'} · {snapshot?.piezo?.site_id ?? '—'} · clipped {snapshot?.piezo?.clipped ? 'yes' : 'no'}</p>
        <SignalScope samples={snapshot?.piezo_waveform ?? []} label="Piezo contact waveform" color="#b45309" large />
        <p className="mt-1 text-xs">ADC counts are not acceleration in g. The inventory has one disk, assigned as a surface contact receiver.</p>
      </article>
      <article className="ops-card">
        <h3 className="font-semibold">Rover and motor</h3>
        <SignalScope samples={snapshot?.rover_trace?.left ?? []} secondary={snapshot?.rover_trace?.right ?? []} label="Encoder ticks" large />
        <p className="mt-2 text-sm">{snapshot?.rover_trace?.note ?? 'Encoder ticks appear when the walk is running or the controller sends ENC.'}</p>
        <p className="text-xs text-slate-500">Heading {snapshot?.pose?.heading_deg ?? '—'} · pose source {snapshot?.pose?.source ?? 'none'}</p>
      </article>
      <article className="ops-card">
        <h3 className="font-semibold">Knock source</h3>
        <p className="mt-2 text-lg">{snapshot?.solenoid.state ?? 'DISARMED'}</p>
        <p className="text-xs">Output energized: {snapshot?.solenoid.output_energized ? 'yes' : 'no'} · reference piezo {snapshot?.solenoid.reference_sensor ?? 'not_in_inventory'}</p>
        <p className="mt-1 text-xs text-slate-500">{snapshot?.solenoid.note}</p>
      </article>
      <article className="ops-card">
        <h3 className="font-semibold">Connectivity</h3>
        <ul className="mt-2 max-h-40 space-y-1 overflow-auto text-xs">
          {(snapshot?.devices ?? []).map((device) => (
            <li key={device.device_id} className="flex justify-between gap-2 border-b border-slate-100 py-1">
              <span>{device.device_id}</span>
              <span>{device.state} · {device.source_mode}</span>
            </li>
          ))}
        </ul>
      </article>
    </div>
  )
}

function Waveform({ values }: { values: number[] }) {
  if (values.length === 0) return <p className="mt-3 text-sm text-slate-500">No acoustic samples.</p>
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = Math.max(1, max - min)
  const step = 100 / values.length
  const path = values
    .map((value, index) => {
      const x = index * step
      const y = 40 - ((value - min) / span) * 36
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
  return (
    <svg viewBox="0 0 100 40" className="mt-3 h-16 w-full" role="img" aria-label="Acoustic envelope in dBFS">
      <path d={path} fill="none" stroke="#2463eb" strokeWidth="1.2" />
    </svg>
  )
}
