import { requestAdvisory } from '../../api/operations'
import type { ActionRunner } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import { evidenceHeadline, nvidiaLive } from '../live/format'
import DetailDialog from './DetailDialog'

export default function EvidenceDetailDialog({
  open,
  snapshot,
  run,
  onClose,
}: {
  open: boolean
  snapshot: OperationsSnapshot | null
  run: ActionRunner
  onClose: () => void
}) {
  const reasoning = snapshot?.reasoning
  const nvidia = nvidiaLive(snapshot)
  const provider = nvidia
    ? `NVIDIA ${reasoning?.model_id} · Nebius Token Factory`
    : reasoning?.provider === 'deterministic_safety_fallback'
      ? 'Rule-based advisory'
      : 'AI: not configured'

  return (
    <DetailDialog open={open} onClose={onClose} title="Evidence and reasoning" state={nvidia ? 'LIVE' : 'UNCONFIGURED'}>
      <p className="summary-title">{evidenceHeadline(snapshot)}</p>
      <p>{provider}</p>
      <p className="quiet-line">{reasoning?.summary ?? 'No advisory has been requested.'}</p>
      <p className="quiet-line">Uncalibrated. A numeric score from the local readout is not a probability and is not an NVIDIA result.</p>
      <h3 className="dialog-subhead">Hypotheses</h3>
      <ul className="plain-list">
        {(reasoning?.hypotheses ?? []).map((item) => (
          <li key={item.label}>
            {item.label} · {item.score === null ? 'not scored' : item.score} · {item.evidence_event_ids.join(', ') || 'no event ids'}
            <span className="quiet-line">{item.limitations.join(' ')}</span>
          </li>
        ))}
        {(reasoning?.hypotheses.length ?? 0) === 0 ? <li>No hypothesis list yet.</li> : null}
      </ul>
      <h3 className="dialog-subhead">Recommendation</h3>
      <p>{reasoning ? `${reasoning.recommendation.type} ${reasoning.recommendation.point_id ?? ''} — approval required. Status: RECOMMENDATION.` : 'No recommendation.'}</p>
      <p className="quiet-line">This text is not a validated command, not sent, and not acknowledged. It cannot energize motors or the solenoid.</p>
      {reasoning?.unknowns?.length ? <p className="quiet-line">Unknowns: {reasoning.unknowns.join('; ')}</p> : null}
      <p className="quiet-line">Event ids: {reasoning?.event_ids.join(', ') || 'none'} · latency {reasoning?.latency_ms ?? '—'} ms · {reasoning?.validation_status ?? snapshot?.ai.status ?? '—'}</p>
      <button
        type="button"
        className="btn"
        onClick={() => void run(async () => {
          await requestAdvisory()
          return 'Local readout requested. It is not an NVIDIA call.'
        })}
      >
        Request rule-based readout
      </button>
    </DetailDialog>
  )
}
