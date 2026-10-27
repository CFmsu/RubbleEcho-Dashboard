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
      <p>{reasoning?.narrative?.trim() || reasoning?.summary || 'No briefing yet. Finish a stop, then download the page.'}</p>
      <p className="quiet-line">{provider}. The page includes the camera frame. It does not move the rover.</p>
      <a className="btn primary" href="/api/briefing.pdf">Download the briefing</a>
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
