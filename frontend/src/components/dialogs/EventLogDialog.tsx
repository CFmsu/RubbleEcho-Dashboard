import { useState } from 'react'
import type { OperationsSnapshot } from '../../types/operations'
import { clockLabel } from '../live/format'
import DetailDialog from './DetailDialog'

export default function EventLogDialog({
  open,
  snapshot,
  onClose,
}: {
  open: boolean
  snapshot: OperationsSnapshot | null
  onClose: () => void
}) {
  const events = snapshot?.events ?? []
  const devices = ['all', ...new Set(events.map((event) => event.device ?? event.sensor ?? 'unknown'))]
  const [device, setDevice] = useState('all')
  const visible = events.filter((event) => device === 'all' || (event.device ?? event.sensor) === device)

  const download = () => {
    const lines = visible.map((event) => JSON.stringify(event)).join('\n')
    const blob = new Blob([lines], { type: 'application/x-ndjson' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'events-window.jsonl'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <DetailDialog open={open} onClose={onClose} title="Event timeline" state={`${visible.length} in view`}>
      <div className="button-row">
        <label>
          Device
          <select value={device} onChange={(event) => setDevice(event.target.value)}>
            {devices.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <button type="button" className="btn" disabled={visible.length === 0} onClick={download}>Download JSONL</button>
      </div>
      <p className="quiet-line">This is the current snapshot window, newest first. It is not a full trial archive.</p>
      {visible.length === 0 ? <p>No events yet</p> : null}
      <table className="event-table">
        <thead>
          <tr><th>Time</th><th>Device</th><th>Event</th><th>Value</th></tr>
        </thead>
        <tbody>
          {visible.map((event) => (
            <tr key={event.event_id}>
              <td>{clockLabel(event.captured_at_utc)}</td>
              <td>{event.device ?? event.sensor ?? '—'}</td>
              <td>{event.summary ?? event.event_id}<span className="quiet-line">{event.event_id} · {event.mode} · {event.quality}</span></td>
              <td>{event.value ?? '—'} {event.unit ?? ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </DetailDialog>
  )
}
