import Panel from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import { deviceOnline } from './format'

export default function OperatorControls({
  snapshot,
  connected,
  hasToken,
  notice,
  error,
  onOpen,
  onHold,
  onReplay,
}: {
  snapshot: OperationsSnapshot | null
  connected: boolean
  hasToken: boolean
  notice: string
  error: string
  onOpen: OpenDialog
  onHold: () => void
  onReplay: () => void
}) {
  const counts = deviceOnline(snapshot)
  const phase = snapshot?.mission_phase ?? 'IDLE'
  const holdDisabled = !connected || phase === 'IDLE' || phase === 'ESTOP'
  const replayDisabled = !connected || !hasToken
  const exportDisabled = !snapshot?.trial_id

  return (
    <Panel
      className="operator-panel"
      testId="operator-panel"
      title="Rover and health"
      state={snapshot?.safety_state ?? 'HOLD'}
      expandLabel="rover controls"
      onExpand={() => onOpen({ kind: 'rover' })}
    >
      <div className="operator-stack">
        <p className="quiet-line">Motion {snapshot?.safety_state ?? '—'} · encoders —</p>
        <p className="quiet-line">{snapshot?.solenoid.state ?? 'DISARMED'} · output locked</p>
        <button type="button" className="health-chip" onClick={() => onOpen({ kind: 'diagnostics' })}>
          {counts.online}/{counts.total || '—'} devices online
        </button>
        <div className="button-row">
          <span title={holdDisabled ? 'No scan is running.' : 'Local hold. Disarms the knock request.'}>
            <button type="button" className="btn" disabled={holdDisabled} onClick={onHold}>Pause</button>
          </span>
          <span title={replayDisabled ? 'Set the operator token in Diagnostics.' : 'Load the labeled replay fixture.'}>
            <button type="button" className="btn" disabled={replayDisabled} onClick={onReplay}>Load replay</button>
          </span>
          <span title={exportDisabled ? 'No trial is open.' : 'Choose an export format.'}>
            <button type="button" className="btn" disabled={exportDisabled} onClick={() => onOpen({ kind: 'export' })}>Export</button>
          </span>
        </div>
        <div className="button-row">
          <span title={!hasToken ? 'Set the operator token in Diagnostics.' : 'Clears the on-screen view. Downloaded files stay.'}>
            <button type="button" className="btn" disabled={!hasToken} onClick={() => onOpen({ kind: 'reset' })}>Reset view</button>
          </span>
        </div>
        <p className="quiet-line" role="status">{error || notice}</p>
      </div>
    </Panel>
  )
}
