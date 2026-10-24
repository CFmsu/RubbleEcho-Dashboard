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
        {events.length === 0 ? <p className="quiet-line">No events yet</p> : null}
        <ol className="event-list">
          {events.map((event) => (
            <li key={event.event_id} className="event-row">
              <span>{clockLabel(event.captured_at_utc)}</span>
              <span>{event.device ?? event.sensor ?? '—'}</span>
              <span title={event.summary}>{event.summary ?? event.event_id}</span>
            </li>
          ))}
        </ol>
        <button type="button" className="text-btn" onClick={() => onOpen({ kind: 'events' })}>See all</button>
      </div>
    </Panel>
  )
}
