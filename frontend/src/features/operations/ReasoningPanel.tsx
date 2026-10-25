import type { OperationsSnapshot } from '../../types/operations'

function costLine(usage: NonNullable<OperationsSnapshot['ai_usage']>): string {
  const dollars = usage.estimated_usd
  const money = dollars < 0.01 ? `$${dollars.toFixed(6)}` : `$${dollars.toFixed(4)}`
  const stages = usage.calls.map((call) => call.stage).join(', ')
  return `${money} catalog estimate · ${usage.total_tokens} tokens · ${stages}. Not an invoice.`
}

export default function ReasoningPanel({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const reasoning = snapshot?.reasoning
  const nvidia = Boolean(snapshot?.nvidia_online && reasoning?.provider === 'nebius_token_factory' && reasoning.live_call)
  const local = reasoning?.provider === 'deterministic_safety_fallback'
  const configured = Boolean(snapshot?.ai?.model_id)
  const heading = nvidia
    ? `NVIDIA ${reasoning?.model_id} · Nebius Token Factory`
    : local && configured
      ? 'Local readout. The NVIDIA model has not answered this card.'
      : local
        ? 'Rule-based, offline'
        : 'AI not configured'
  return (
    <section className="ops-card">
      <h2 className="text-xl font-semibold">AI reasoning and sensor fusion</h2>
      <p className="mt-1 text-sm font-medium">{heading}</p>
      <p className="mt-2 text-sm">{reasoning?.summary ?? snapshot?.ai.message ?? 'No advisory has been requested.'}</p>
      <p className="mt-2 text-xs text-slate-500">
        Advisory only · {reasoning?.score_semantics ?? 'not a model score'} · latency {reasoning?.latency_ms ?? '—'} ms · status {reasoning?.validation_status ?? snapshot?.ai.status ?? '—'}
      </p>
      {snapshot?.scene_note ? <p className="mt-2 text-sm">Scene: {snapshot.scene_note.scene}</p> : null}
      {snapshot?.ai_usage && snapshot.ai_usage.total_tokens > 0 ? (
        <p className="mt-2 text-xs text-slate-500">{costLine(snapshot.ai_usage)}</p>
      ) : null}
      <ul className="mt-3 space-y-2 text-sm">
        {(reasoning?.hypotheses ?? []).map((item) => (
          <li key={item.label} className="rounded-lg bg-slate-50 p-2">
            <span className="font-medium">{item.label}</span>
            <span className="text-slate-500"> · score {item.score ?? 'not scored'}</span>
            <p className="text-xs text-slate-600">{item.limitations.join(' ')}</p>
          </li>
        ))}
      </ul>
      {reasoning ? (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
          <p className="font-medium">Recommendation requires approval</p>
          <p>{reasoning.recommendation.detail ?? reasoning.recommendation.type} {reasoning.recommendation.point_id ?? ''}</p>
          <p className="text-xs">This text does not move the rover.</p>
        </div>
      ) : (
        <p className="mt-3 text-sm text-slate-600">No model call has been made. Heuristic map scores, when present, are labeled uncalibrated.</p>
      )}
      {reasoning?.unknowns?.length ? <p className="mt-2 text-xs">Unknowns: {reasoning.unknowns.join('; ')}</p> : null}
    </section>
  )
}
