import { useState } from 'react'
import { armSolenoid } from '../../api/operations'
import type { ActionRunner } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
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

  return (
    <DetailDialog open={open} onClose={onClose} title="Rover and knock request" state={snapshot?.safety_state ?? 'HOLD'}>
      <FactGrid
        rows={[
          ['Controller', 'Arduino Uno + Cytron MDD10A'],
          ['Motion', snapshot?.safety_state ?? '—'],
          ['Left encoder', '—'],
          ['Right encoder', '—'],
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
      <p className="quiet-line">Encoder counts stay blank until the motor controller reports them. A heading is shown only with a pose source.</p>
      <label className="check-line">
        <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
        I confirm this is a bench request. Arming does not energize the 12 V circuit.
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
