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
  onListen,
  onRadarDummy,
  onRadarLive,
  onPiMimic,
  onPlan,
  onObstacle,
  onSignal,
  compact = false,
}: {
  snapshot: OperationsSnapshot | null
  connected: boolean
  hasToken: boolean
  notice: string
  error: string
  onOpen: OpenDialog
  onHold: () => void
  onReplay: () => void
  onListen: () => void
  onRadarDummy: () => void
  onRadarLive: () => void
  onPiMimic: () => void
  onPlan: () => void
  onObstacle: () => void
  onSignal: () => void
  compact?: boolean
}) {
  const counts = deviceOnline(snapshot)
  const phase = snapshot?.mission_phase ?? 'IDLE'
  const holdDisabled = !connected || phase === 'IDLE' || phase === 'ESTOP'
  const replayDisabled = !connected || !hasToken
  const exportDisabled = !snapshot?.trial_id
  const listening = snapshot?.devices?.some((device) => device.device_id === 'xvf3800' && device.source_mode === 'live') ?? false
  const radarLive = snapshot?.devices?.some((device) => device.device_id === 'mr60bha2' && device.source_mode === 'live') ?? false
  const radarDummy = snapshot?.radar?.case_name === 'dummy_mr60bha2'
  const piMimic = snapshot?.radar?.case_name === 'Pi mimic'

  const buttons = (
    <>
      <div className="button-row">
        <span title={holdDisabled ? 'No scan is running.' : 'Local hold. Disarms the knock request.'}>
          <button type="button" className="btn" disabled={holdDisabled} onClick={onHold}>Pause</button>
        </span>
        <span title={connected ? 'Open the XVF3800 raw 6-channel stream and run the knock and scratch detector.' : 'Backend is not connected.'}>
          <button type="button" className="btn" disabled={!connected} onClick={onListen}>{listening ? 'Stop mic' : 'Listen'}</button>
        </span>
        <span title={connected ? 'Open the XIAO serial port and read presence, breath, heart, distance, and targets.' : 'Backend is not connected.'}>
          <button type="button" className="btn" disabled={!connected} onClick={onRadarLive}>{radarLive ? 'Stop radar' : 'Read radar'}</button>
        </span>
        <span title={connected ? 'Play the lines a Raspberry Pi would send. No Pi is connected.' : 'Backend is not connected.'}>
          <button type="button" className="btn" disabled={!connected} onClick={onPiMimic}>{piMimic ? 'Stop mimic' : 'Mimic Pi'}</button>
        </span>
        <span title={connected ? 'Show the MR60BHA2 fields with dummy samples until the module is plugged in.' : 'Backend is not connected.'}>
          <button type="button" className="btn" disabled={!connected || radarLive} onClick={onRadarDummy}>{radarDummy ? 'Stop dummy' : 'Dummy radar'}</button>
        </span>
        <span title="If a knock, scratch, or radar presence is in the latest sample, paint the heatmap and ask where to listen next.">
          <button type="button" className="btn" disabled={!connected} onClick={onSignal}>Read signals</button>
        </span>
        <span title="Build the virtual boundary and the order of the grid cells. Motors are not commanded.">
          <button type="button" className="btn" disabled={!connected} onClick={onPlan}>Plan grid</button>
        </span>
        <span title="If the ultrasonic reading is inside 20 cm, block the next cell and rotate the planned look.">
          <button type="button" className="btn" disabled={!connected} onClick={onObstacle}>Guard obstacle</button>
        </span>
      </div>
      {error || notice ? <p className="quiet-line" role="status">{error || notice}</p> : null}
    </>
  )

  if (compact) return <div className="acquire-bar">{buttons}</div>

  return (
    <Panel
      className="operator-panel"
      testId="operator-panel"
      title="Rover and health"
      state={snapshot?.mission_phase === 'IDLE' ? 'IDLE' : snapshot?.safety_state ?? 'HOLD'}
      expandLabel="rover controls"
      onExpand={() => onOpen({ kind: 'rover' })}
    >
      <div className="operator-stack">
        <p className="quiet-line">
          Motion {snapshot?.mission_phase === 'LISTEN' ? 'LISTEN' : snapshot?.run_active ? 'RUN' : snapshot?.mission_phase ?? 'IDLE'}
          {' · '}
          {snapshot?.rover_trace ? `L ${snapshot.rover_trace.left_counts} R ${snapshot.rover_trace.right_counts}` : 'encoders —'}
        </p>
        <p className="quiet-line">{snapshot?.solenoid.state ?? 'DISARMED'} · A0 · 3×200 ms</p>
        <button type="button" className="health-chip" onClick={() => onOpen({ kind: 'diagnostics' })}>
          {counts.online}/{counts.total || '—'} {snapshot?.mode === 'simulation' ? 'simulated' : 'devices online'}
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
          <span title={connected ? 'Open the XVF3800 raw 6-channel stream and run the knock and scratch detector.' : 'Backend is not connected.'}>
            <button type="button" className="btn" disabled={!connected} onClick={onListen}>{listening ? 'Stop mic' : 'Listen'}</button>
          </span>
          <span title={connected ? 'Show the MR60BHA2 fields with dummy samples until the module is plugged in.' : 'Backend is not connected.'}>
            <button type="button" className="btn" disabled={!connected || radarLive} onClick={onRadarDummy}>{radarDummy ? 'Stop dummy' : 'Dummy radar'}</button>
          </span>
          <span title={connected ? 'Open the XIAO serial port and read presence, breath, heart, distance, and targets.' : 'Backend is not connected.'}>
            <button type="button" className="btn" disabled={!connected} onClick={onRadarLive}>{radarLive ? 'Stop radar' : 'Read radar'}</button>
          </span>
          <span title={connected ? 'Play the lines a Raspberry Pi would send. The sweep uses that stand-in. No Pi is connected.' : 'Backend is not connected.'}>
            <button type="button" className="btn" disabled={!connected} onClick={onPiMimic}>{piMimic ? 'Stop mimic' : 'Mimic Pi'}</button>
          </span>
        </div>
        <div className="button-row">
          <span title="Build the virtual boundary and the order of the six grid cells. Motors are not commanded.">
            <button type="button" className="btn" disabled={!connected} onClick={onPlan}>Plan grid</button>
          </span>
          <span title="If the ultrasonic reading is inside 20 cm, block the next cell and rotate the planned look.">
            <button type="button" className="btn" disabled={!connected} onClick={onObstacle}>Guard obstacle</button>
          </span>
          <span title="If a knock, scratch, or radar presence is in the latest sample, paint the heatmap and ask where to listen next.">
            <button type="button" className="btn" disabled={!connected} onClick={onSignal}>Read signals</button>
          </span>
        </div>
        <p className="quiet-line" role="status">{error || notice}</p>
      </div>
    </Panel>
  )
}
