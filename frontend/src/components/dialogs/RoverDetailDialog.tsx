import { useState } from 'react'
import { armSolenoid } from '../../api/operations'
import type { ActionRunner } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import SignalScope from '../live/SignalScope'
import DetailDialog, { FactGrid } from './DetailDialog'

export default function RoverDetailDialog({
  open,
  snapshot,
  hasToken,
  run,
  onClose,
}: {
  open: boolean
  snapshot: OperationsSnapshot | null
  hasToken: boolean
  run: ActionRunner
  onClose: () => void
}) {
  const [consent, setConsent] = useState(false)
  const [result, setResult] = useState('')
  const solenoid = snapshot?.solenoid
  const trace = snapshot?.rover_trace

  return (
    <DetailDialog open={open} onClose={onClose} title="Rover and knock request" state={snapshot?.mission_phase === 'LISTEN' ? 'LISTEN' : snapshot?.safety_state ?? 'HOLD'}>
      <SignalScope
        samples={trace?.left ?? []}
        secondary={trace?.right ?? []}
        label="Left encoder in blue, right encoder in amber"
        large
      />
      <p className="quiet-line">{trace?.note ?? 'Encoder ticks appear when the walk is running or the controller sends ENC.'}</p>
      <FactGrid
        rows={[
          ['Controller', 'Arduino Uno + Cytron MDD10A'],
          ['Motion', snapshot?.mission_phase === 'LISTEN' ? 'LISTEN' : snapshot?.safety_state ?? '—'],
          ['Left encoder', trace ? `${trace.left_counts} ${trace.unit}` : '—'],
          ['Right encoder', trace ? `${trace.right_counts} ${trace.unit}` : '—'],
          ['Pose', snapshot?.pose?.valid ? `${snapshot.pose.x_cm} cm, ${snapshot.pose.y_cm} cm` : 'unavailable'],
          ['Heading', snapshot?.pose?.heading_deg == null ? '—' : `${snapshot.pose.heading_deg}°`],
          ['Last command', '—'],
          ['Knock state', solenoid?.state ?? 'DISARMED'],
          ['Output energized', solenoid?.output_energized ? 'yes' : 'no'],
          ['Reference piezo', solenoid?.reference_sensor ?? 'not_in_inventory'],
          ['Pulses logged', String(solenoid?.pulses_logged ?? 0)],
        ]}
      />
      <p className="quiet-line">{solenoid?.note ?? 'GPIO output is locked.'}</p>
      <p className="quiet-line">A return inside 20 cm blocks the next grid cell. The rover turns toward the open cell and listens before it rolls again. An ENC line fills these same ticks.</p>
      <label className="check-line">
        <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
        I confirm this is a bench request. Arming allows a later knock to drive Arduino pin A0.
      </label>
      <button
        type="button"
        className="btn"
        disabled={!hasToken || !consent || solenoid?.state === 'ARMED'}
        onClick={() => {
          void run(async () => {
            const message = await armSolenoid(true)
            return message
          }).then((message) => setResult(message ?? '')).catch((caught: unknown) => {
            setResult(caught instanceof Error ? caught.message : 'Arm failed')
          })
        }}
      >
        Arm knock request
      </button>
      {result ? <p role="status">{result}</p> : null}
    </DetailDialog>
  )
}
