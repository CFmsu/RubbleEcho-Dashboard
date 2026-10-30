import type { OperationsSnapshot } from '../../types/operations'

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
      <h2 className="text-xl font-semibold">Where to walk first</h2>
      <p className="mt-1 text-sm font-medium">{heading}</p>
      <p className="mt-2 text-sm">{reasoning?.narrative?.trim() || reasoning?.summary || snapshot?.ai.message || 'No briefing yet. Finish a stop, then download the page.'}</p>
      {snapshot?.scene_note ? <p className="mt-2 text-sm">{snapshot.scene_note.scene}</p> : null}
      <a className="btn primary" href="/api/briefing.pdf">Download the briefing</a>
      <p className="mt-2 text-xs text-slate-500">It names a square to check. It does not move the rover.</p>
    </section>
  )
}
