import Panel from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import RangeLane from './RangeLane'
import { panelState } from './format'
import SignalScope from './SignalScope'

export default function SignalWall({
  snapshot,
  onOpen,
}: {
  snapshot: OperationsSnapshot | null
  onOpen: OpenDialog
}) {
  const ultrasonic = snapshot?.ultrasonic
  const acoustic = snapshot?.acoustic
  const piezo = snapshot?.piezo
  const trace = snapshot?.rover_trace
  const listening = snapshot?.mission_phase === 'LISTEN'

  return (
    <>
      <Panel
        className="wave-card"
        title="Ultrasonic"
        state={panelState(ultrasonic?.source_mode)}
        expandLabel="ultrasonic reading"
        onExpand={() => onOpen({ kind: 'ultrasonic' })}
      >
        <p className="wave-value">{ultrasonic?.distance_cm == null ? '—' : ultrasonic.distance_cm}<small> cm</small></p>
        <div className="wave-figure">
          <RangeLane distanceCm={ultrasonic?.distance_cm ?? null} echoTimeout={Boolean(ultrasonic?.echo_timeout)} />
        </div>
        <p className="quiet-line">{ultrasonic ? `${ultrasonic.direction} · ${ultrasonic.quality}` : 'Waiting for an echo'} · amber is inside the 20 cm stop</p>
      </Panel>
      <Panel
        className="wave-card"
        title="Acoustic"
        state={panelState(acoustic?.source_mode)}
        expandLabel="acoustic reading"
        onExpand={() => onOpen({ kind: 'audio' })}
      >
        <p className="wave-value">{acoustic?.class ?? '—'}</p>
        <div className="wave-figure">
          <SignalScope samples={snapshot?.acoustic_waveform ?? []} label="Acoustic waveform" instrument color="#2563eb" />
        </div>
        <p className="quiet-line">
          {acoustic?.source_mode === 'live'
            ? `Live USB mic · ${acoustic.rms_dbfs == null ? 'measuring' : `${acoustic.rms_dbfs.toFixed(1)} dBFS`} · local shape rules, not the NVIDIA model`
            : listening
              ? 'Listening'
              : acoustic?.rms_dbfs == null
                ? 'No samples'
                : `${acoustic.rms_dbfs.toFixed(1)} dBFS`}
        </p>
      </Panel>
      <Panel
        className="wave-card"
        title="Vibration"
        state={panelState(piezo?.source_mode)}
        expandLabel="vibration reading"
        onExpand={() => onOpen({ kind: 'vibration' })}
      >
        <p className="wave-value">{piezo ? piezo.peak_adc_counts : '—'}<small>{piezo ? ' counts' : ''}</small></p>
        <div className="wave-figure">
          <SignalScope samples={snapshot?.piezo_waveform ?? []} label="Piezo contact waveform" instrument color="#b45309" />
        </div>
        <p className="quiet-line">{piezo?.contact_state ?? 'No contact sample'}</p>
      </Panel>
      <Panel
        className="wave-card"
        title="Rover"
        state={trace ? panelState(trace.source_mode) : 'DISCONNECTED'}
        expandLabel="rover reading"
        onExpand={() => onOpen({ kind: 'rover' })}
      >
        <p className="wave-value">{trace ? `${trace.left_counts}` : '—'}<small>{trace ? ` / ${trace.right_counts}` : ''}</small></p>
        <div className="wave-figure">
          <SignalScope
            samples={trace?.left ?? []}
            secondary={trace?.right ?? []}
            label="Left and right encoder ticks"
            instrument
            color="#2563eb"
            secondaryColor="#b45309"
          />
        </div>
        <p className="quiet-line">{trace ? 'Left in blue, right in amber' : 'Encoders quiet'}</p>
      </Panel>
    </>
  )
}
