import Panel from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import { clockLabel, panelState } from './format'

export default function EventSummary({
  snapshot,
  onOpen,
}: {
  snapshot: OperationsSnapshot | null
  onOpen: OpenDialog
}) {
  const events = (snapshot?.events ?? []).slice(0, 5)
  return (
    <Panel
      testId="event-panel"
      title="Event timeline"
      state={panelState(snapshot?.mode)}
      expandLabel="event timeline"
      onExpand={() => onOpen({ kind: 'events' })}
    >
      <div className="event-stack">
        {events.length === 0 ? <p className="quiet-line">No events yet</p> : (
          <div className="index-wrap">
            <table className="index-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Device</th>
                  <th>Event</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.event_id}>
                    <td>{clockLabel(event.captured_at_utc)}</td>
                    <td>{event.device ?? event.sensor ?? '—'}</td>
                    <td title={event.summary}>{event.summary ?? event.event_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <button type="button" className="text-btn" onClick={() => onOpen({ kind: 'events' })}>See all</button>
      </div>
    </Panel>
  )
}
