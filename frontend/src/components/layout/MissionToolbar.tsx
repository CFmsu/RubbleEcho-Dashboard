import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'

export default function MissionToolbar({
  snapshot,
  hasToken,
  status,
  onOpen,
  onCapture,
  onRun,
  onStop,
}: {
  snapshot: OperationsSnapshot | null
  hasToken: boolean
  status: string
  onOpen: OpenDialog
  onCapture: () => void
  onRun: () => void
  onStop: () => void
}) {
  const trial = snapshot?.trial_id ? snapshot.trial_id : 'No trial'
  const phase = snapshot?.run_active ? snapshot.scan_stage ?? 'SCANNING' : snapshot?.mission_phase ?? 'IDLE'
  const camerasReady = (snapshot?.streaming_camera_count ?? 0) > 0 || Boolean(snapshot?.cameras?.some((camera) => camera.image_url))
  const knockArmed = snapshot?.solenoid.state === 'ARMED' && hasToken
  const canExport = Boolean(snapshot?.trial_id)
  const running = Boolean(snapshot?.run_active)
  const elapsed = snapshot?.mode === 'simulation' && snapshot.run_elapsed_s != null ? `${Math.round(snapshot.run_elapsed_s)}s` : '—'
  const meta = `${trial} · cover not recorded · ${phase} · runtime ${elapsed}`

  return (
    <div className="mission-toolbar" data-testid="mission-toolbar">
      <p className="toolbar-meta" title={status ? `${meta} · ${status}` : meta}>
        {meta}{status ? ` · ${status}` : ''}
      </p>
      <div className="toolbar-actions">
        <span title={running ? 'A simulation is already walking the six points.' : 'Start the labeled simulation. It does not command motors or mark hardware live.'}>
          <button type="button" className="btn primary" disabled={running} onClick={onRun}>Run</button>
        </span>
        <span title="Stop the simulation and return the console to idle.">
          <button type="button" className="btn danger" onClick={onStop}>Stop</button>
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
