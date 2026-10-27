import { useEffect, type ReactNode } from 'react'
import { ExpandIcon } from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { DialogRequest } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import EchoDiagram from './EchoDiagram'
import { panelState } from './format'
import { noteRange } from './rangeTrace'
import SignalScope from './SignalScope'

export default function SensorStrip({
  snapshot,
  onOpen,
}: {
  snapshot: OperationsSnapshot | null
  onOpen: OpenDialog
}) {
  const ultrasonic = snapshot?.ultrasonic
  const acoustic = snapshot?.acoustic
  const piezo = snapshot?.piezo
  const waveform = snapshot?.acoustic_waveform ?? []
  const vibration = snapshot?.piezo_waveform ?? []
  const roverTrace = snapshot?.rover_trace
  const listening = snapshot?.mission_phase === 'LISTEN'
  useEffect(() => {
    noteRange(ultrasonic?.distance_cm)
    const id = window.setInterval(() => noteRange(ultrasonic?.distance_cm), 450)
    return () => window.clearInterval(id)
  }, [ultrasonic?.distance_cm])

  return (
    <>
      <Strip
        title="Ultrasonic"
        state={panelState(ultrasonic?.source_mode)}
        value={ultrasonic?.distance_cm == null ? '—' : String(ultrasonic.distance_cm)}
        unit="cm"
        detail={ultrasonic ? `${ultrasonic.direction} · ${ultrasonic.quality}` : 'No sample'}
        expandLabel="ultrasonic"
        request={{ kind: 'ultrasonic' }}
        onOpen={onOpen}
        extra={<EchoDiagram compact distanceCm={ultrasonic?.distance_cm ?? null} echoTimeout={Boolean(ultrasonic?.echo_timeout)} />}
      />
      <Strip
        title="Acoustic"
        state={panelState(acoustic?.source_mode)}
        value={acoustic?.rms_dbfs == null ? '—' : acoustic.rms_dbfs.toFixed(1)}
        unit={acoustic?.rms_dbfs == null ? '' : 'dBFS'}
        detail={listening ? `Listening · ${acoustic?.class ?? 'no class'}` : acoustic ? acoustic.class : 'No samples'}
        expandLabel="acoustic"
        request={{ kind: 'audio' }}
        onOpen={onOpen}
        extra={<SignalScope samples={waveform} label="Acoustic waveform" />}
      />
      <Strip
        title="Vibration"
        state={panelState(piezo?.source_mode)}
        value={piezo ? String(piezo.peak_adc_counts) : '—'}
        unit={piezo ? 'counts' : ''}
        detail={piezo ? piezo.contact_state : 'No contact sample'}
        expandLabel="vibration"
        request={{ kind: 'vibration' }}
        onOpen={onOpen}
        extra={<SignalScope samples={vibration} label="Piezo contact waveform" color="#b45309" />}
      />
      <Strip
        title="Rover"
        state={roverTrace ? panelState(roverTrace.source_mode) : snapshot?.pose?.valid ? panelState(snapshot.mode) : 'DISCONNECTED'}
        value={listening ? 'LISTEN' : snapshot?.mission_phase === 'SIGNS' || snapshot?.mission_phase === 'VITALS' || snapshot?.mission_phase === 'TURN' ? snapshot.mission_phase : snapshot?.run_active ? 'RUN' : snapshot?.mission_phase && snapshot.mission_phase !== 'IDLE' ? snapshot.mission_phase : 'IDLE'}
        unit=""
        detail={roverTrace ? `L ${roverTrace.left_counts} · R ${roverTrace.right_counts}` : `Encoders — · ${snapshot?.solenoid.state ?? 'DISARMED'}`}
        expandLabel="rover"
        request={{ kind: 'rover' }}
        onOpen={onOpen}
        extra={<SignalScope samples={roverTrace?.left ?? []} secondary={roverTrace?.right ?? []} label="Left and right encoder ticks" />}
      />
    </>
  )
}

function Strip({
  title,
  state,
  value,
  unit,
  detail,
  expandLabel,
  request,
  onOpen,
  extra,
}: {
  title: string
  state: string
  value: string
  unit: string
  detail: string
  expandLabel: string
  request: DialogRequest
  onOpen: OpenDialog
  extra?: ReactNode
}) {
  return (
    <div className="sensor-strip">
      <button type="button" className="sensor-main" onClick={() => onOpen(request)}>
        <span className="sensor-name">{title}<span className="state-pill" data-state={state}>{state}</span></span>
        <span className="sensor-value">{value}{unit ? <small>{unit}</small> : null}</span>
        <span className="sensor-detail">
          <span>{detail}</span>
          {extra}
        </span>
      </button>
      <button type="button" className="expand-btn" aria-label={`Expand ${expandLabel}`} title={`Expand ${expandLabel}`} onClick={() => onOpen(request)}>
        <ExpandIcon />
      </button>
    </div>
  )
}

