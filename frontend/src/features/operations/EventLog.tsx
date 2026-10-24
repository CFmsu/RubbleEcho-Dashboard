import type { OperationsSnapshot } from '../../types/operations'

export default function EventLog({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const events = snapshot?.events ?? []
  return (
    <section className="ops-card">
      <h2 className="text-xl font-semibold">Event log</h2>
      {events.length === 0 ? <p className="mt-3 text-sm text-slate-500">No events.</p> : null}
      <ol className="mt-3 max-h-80 space-y-2 overflow-auto">
        {events.map((event) => (
          <li key={event.event_id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
            <span className="font-mono text-xs text-slate-500">{event.captured_at_utc ?? '—'} · {event.event_id}</span>
            <p>{event.summary}</p>
            <p className="text-xs text-slate-500">{event.device} · {event.quality} · {event.mode} · {event.value ?? '—'} {event.unit ?? ''}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
