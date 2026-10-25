import { useEffect, useRef, type ReactNode } from 'react'
import { ExpandIcon } from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { DialogRequest } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import { panelState } from './format'
import { heartbeatPath, noteRange } from './rangeTrace'

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
  const envelope = snapshot?.acoustic_envelope_dbfs ?? []
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
        extra={<RangeSpark active={ultrasonic?.distance_cm != null} />}
      />
      <Strip
        title="Acoustic"
        state={panelState(acoustic?.source_mode)}
        value={acoustic?.rms_dbfs == null ? '—' : acoustic.rms_dbfs.toFixed(1)}
        unit={acoustic?.rms_dbfs == null ? '' : 'dBFS'}
        detail={acoustic ? acoustic.class : 'No samples'}
        expandLabel="acoustic"
        request={{ kind: 'audio' }}
        onOpen={onOpen}
        extra={envelope.length > 0 ? <Envelope values={envelope} /> : null}
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
      />
      <Strip
        title="Rover"
        state={snapshot?.pose?.valid ? panelState(snapshot.mode) : 'DISCONNECTED'}
        value={snapshot?.run_active ? 'RUN' : snapshot?.mission_phase && snapshot.mission_phase !== 'IDLE' ? snapshot.mission_phase : 'IDLE'}
        unit=""
        detail={`Encoders — · ${snapshot?.solenoid.state ?? 'DISARMED'}`}
        expandLabel="rover"
        request={{ kind: 'rover' }}
        onOpen={onOpen}
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

function RangeSpark({ active }: { active: boolean }) {
  const pathRef = useRef<SVGPathElement>(null)
  useEffect(() => {
    if (!active || !pathRef.current) return
    let frame = 0
    const started = performance.now()
    const loop = (now: number) => {
      pathRef.current?.setAttribute('d', heartbeatPath((now - started) / 1000, 72, 28))
      frame = requestAnimationFrame(loop)
    }
    frame = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(frame)
  }, [active])
  return (
    <svg viewBox="0 0 72 28" className="pulse" role="img" aria-label="Live obstacle-distance pulse">
      <path ref={pathRef} d={active ? heartbeatPath(0, 72, 28) : 'M0 16 L72 16'} fill="none" stroke={active ? '#16845d' : '#94a3b8'} strokeWidth="1.6" />
    </svg>
  )
}

function Envelope({ values }: { values: number[] }) {
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = Math.max(1, max - min)
  const step = 100 / values.length
  const path = values
    .map((value, index) => {
      const x = index * step
      const y = 24 - ((value - min) / span) * 20
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
  return (
    <svg viewBox="0 0 100 24" className="spark" role="img" aria-label="Acoustic envelope in dBFS">
      <path d={path} fill="none" stroke="#2563eb" strokeWidth="1.4" />
    </svg>
  )
}
