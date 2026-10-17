
type MissionStatusProps = {
  confidence: number
  phase: string
  events: string[]
}

function MissionStatus({
  confidence,
  phase,
  events,
}: MissionStatusProps) {
  const phaseMessages: Record<string, string> = {
    explore: 'The rover is exploring.',
    knock: 'The rover is knocking.',
    listen: 'The rover is listening.',
    decide: 'The rover is choosing the next location.',
  }

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <h3 className="mb-6 text-xl font-semibold">
        Mission Status
      </h3>

      {/* Confidence */}
      <div className="mb-6">
        <p className="text-sm text-slate-500">
          Simulated Confidence
        </p>
        <p className="mt-2 text-5xl font-bold text-blue-600">
          {Math.round(confidence * 100)}%
        </p>
      </div>

      {/* Current Phase */}
      <div className="mb-6 border-t pt-5">
        <h4 className="mb-2 font-semibold">
          Current Phase
        </h4>
        <p className="text-slate-600">
          {phaseMessages[phase] ?? 'The rover is standing by.'}
        </p>
      </div>

      {/* Event Log */}
      <div className="border-t pt-5">
        <h4 className="mb-3 font-semibold">
          Event Log
        </h4>

        <ul className="space-y-2">
          {events.map((event, index) => (
            <li
              key={index}
              className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700"
            >
              {event}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default MissionStatus
