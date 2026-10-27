import Panel from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import { evidenceHeadline, nvidiaLive, panelState } from './format'

export default function ReasoningSummary({
  snapshot,
  onOpen,
}: {
  snapshot: OperationsSnapshot | null
  onOpen: OpenDialog
}) {
  const reasoning = snapshot?.reasoning
  const nvidia = nvidiaLive(snapshot)
  const local = reasoning?.provider === 'deterministic_safety_fallback'
  const configured = Boolean(snapshot?.ai?.model_id)
  const ai = nvidia
    ? `NVIDIA ${reasoning?.model_id ?? ''}`.trim()
    : local && configured
      ? 'Local readout'
      : local
        ? 'Rule-based, offline'
        : 'AI: not configured'
  const recommendation = reasoning?.recommendation.detail ?? reasoning?.recommendation.type ?? 'No recommendation.'
  const chips = [
    ['Acoustic', snapshot?.acoustic ? panelState(snapshot.acoustic.source_mode) : 'No sample'],
    ['Piezo', snapshot?.piezo ? panelState(snapshot.piezo.source_mode) : 'No sample'],
    ['Radar', snapshot?.radar ? panelState(snapshot.radar.source_mode, snapshot.radar.stale) : 'No sample'],
    ['Camera', (snapshot?.streaming_camera_count ?? 0) > 0 ? 'LIVE' : snapshot?.cameras?.some((camera) => camera.image_url) ? 'SIMULATION' : 'No sample'],
    ['Ultrasonic', snapshot?.ultrasonic ? panelState(snapshot.ultrasonic.source_mode) : 'No sample'],
  ] as const

  return (
    <Panel
      testId="evidence-panel"
      title="Evidence"
      state={nvidia ? 'LIVE' : 'UNCONFIGURED'}
      expandLabel="evidence"
      onExpand={() => onOpen({ kind: 'evidence' })}
    >
      <div className="summary-stack">
        <p className="summary-title">{evidenceHeadline(snapshot)}</p>
        <p className="chip-row">
          {chips.map(([label, value]) => (
            <span key={label} className="chip">{label} · {value}</span>
          ))}
        </p>
        <p className="quiet-line">{reasoning?.narrative?.trim() ? 'The briefing names the first square and carries the camera frame.' : recommendation}</p>
        <p className="quiet-line">{ai}</p>
        <a className="btn" href="/api/briefing.pdf">Download the briefing</a>
      </div>
    </Panel>
  )
}
