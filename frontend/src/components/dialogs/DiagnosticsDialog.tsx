import { useState } from 'react'
import { readOperatorToken, writeOperatorToken } from '../../api/operations'
import type { OperationsSnapshot } from '../../types/operations'
import { DEVICE_LABELS, clockLabel } from '../live/format'
import DetailDialog from './DetailDialog'

export default function DiagnosticsDialog({
  open,
  snapshot,
  onToken,
  onClose,
}: {
  open: boolean
  snapshot: OperationsSnapshot | null
  onToken: (token: string) => void
  onClose: () => void
}) {
  const [token, setToken] = useState(readOperatorToken)

  return (
    <DetailDialog open={open} onClose={onClose} title="Diagnostics" state={snapshot?.badge ?? 'DISCONNECTED'}>
      <label className="stack-label" htmlFor="operator-token">
        Operator token
        <input
          id="operator-token"
          type="password"
          autoComplete="off"
          value={token}
          onChange={(event) => {
            setToken(event.target.value)
            writeOperatorToken(event.target.value)
            onToken(event.target.value)
          }}
        />
      </label>
      <p className="quiet-line">The token stays in this browser tab and is sent only to this local API. It is not an NVIDIA key.</p>
      <table className="event-table">
        <thead>
          <tr><th>Device</th><th>State</th><th>Mode</th><th>Seen</th></tr>
        </thead>
        <tbody>
          {(snapshot?.devices ?? []).map((device) => (
            <tr key={device.device_id}>
              <td>{DEVICE_LABELS[device.device_id] ?? device.device_id}</td>
              <td>{device.state}</td>
              <td>{device.source_mode}</td>
              <td>{clockLabel(device.last_seen_utc)}<span className="quiet-line">{device.error ?? device.quality}</span></td>
            </tr>
          ))}
          <tr>
            <td>Cytron MDD10A / encoders</td>
            <td>not enumerated</td>
            <td>unavailable</td>
            <td>Not online because the Uno card exists. Counts stay blank until encoder telemetry arrives.</td>
          </tr>
        </tbody>
      </table>
      <p className="quiet-line">Malformed radar lines this session: {snapshot?.malformed_radar_lines ?? 0}. A row is connected only after a sample or a verified live call.</p>
    </DetailDialog>
  )
}
