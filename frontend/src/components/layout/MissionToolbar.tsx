import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'

export default function MissionToolbar({
  snapshot,
  hasToken,
  onOpen,
  onCapture,
}: {
  snapshot: OperationsSnapshot | null
  hasToken: boolean
  onOpen: OpenDialog
  onCapture: () => void
}) {
  const trial = snapshot?.trial_id ? snapshot.trial_id : 'No trial'
  const phase = snapshot?.mission_phase ?? 'IDLE'
  const camerasReady = (snapshot?.streaming_camera_count ?? 0) > 0
  const knockArmed = snapshot?.solenoid.state === 'ARMED' && hasToken
  const canExport = Boolean(snapshot?.trial_id)

  return (
    <div className="mission-toolbar" data-testid="mission-toolbar">
      <p className="toolbar-meta" title={`${trial} · cover not recorded · ${phase} · runtime —`}>
        {trial} · cover not recorded · {phase} · runtime —
      </p>
      <div className="toolbar-actions">
        <span title="Disabled until live mode reports the radar, ultrasonic, microphone, and top camera connected. This does not command motors.">
          <button type="button" className="btn primary" disabled>Start Scan</button>
        </span>
        <span title={camerasReady ? 'Capture a frame from each open camera.' : 'Disabled until a camera is streaming.'}>
          <button type="button" className="btn" disabled={!camerasReady} onClick={onCapture}>Capture</button>
        </span>
        <span title={knockArmed ? 'Opens a confirmation. The 12 V output stays locked.' : 'Disarmed. Arming is a separate confirmation and does not energize the output.'}>
          <button type="button" className="btn" disabled={!knockArmed} onClick={() => onOpen({ kind: 'knock' })}>Knock Test</button>
        </span>
        <span title={canExport ? 'Choose ZIP, JSON, or CSV.' : 'Disabled until a trial is open.'}>
          <button type="button" className="btn" disabled={!canExport} onClick={() => onOpen({ kind: 'export' })}>Export</button>
        </span>
      </div>
    </div>
  )
}
