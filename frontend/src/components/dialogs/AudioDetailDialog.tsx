import type { OperationsSnapshot } from '../../types/operations'
import { panelState } from '../live/format'
import DetailDialog, { FactGrid } from './DetailDialog'

export default function AudioDetailDialog({
  open,
  snapshot,
  onClose,
}: {
  open: boolean
  snapshot: OperationsSnapshot | null
  onClose: () => void
}) {
  const acoustic = snapshot?.acoustic
  const values = snapshot?.acoustic_envelope_dbfs ?? []
  return (
    <DetailDialog open={open} onClose={onClose} title="ReSpeaker XVF3800" state={panelState(acoustic?.source_mode)}>
      {values.length === 0 ? <p>No samples</p> : <Envelope values={values} />}
      <FactGrid
        rows={[
          ['Class', acoustic?.class ?? 'No samples'],
          ['Level', acoustic?.rms_dbfs == null ? '—' : `${acoustic.rms_dbfs} dBFS`],
          ['Score', acoustic?.model_score == null ? 'Uncalibrated' : `${acoustic.model_score} (${acoustic.score_semantics})`],
          ['Origin', acoustic?.origin_unknown === false ? 'attributed' : 'unknown'],
          ['Site', acoustic?.site_id ?? '—'],
          ['Source', acoustic?.source_mode ?? 'unavailable'],
          ['Channels', 'Not enumerated. Four raw traces are not claimed.'],
        ]}
      />
      <p className="quiet-line">{snapshot?.acoustic_envelope_note ?? 'Levels are dBFS, not dB SPL.'}</p>
      <p className="quiet-line">Nearby speech is not evidence that sound came from a buried box. A knock class still needs the contact sensor and the trial log before it is treated as a buried source.</p>
    </DetailDialog>
  )
}

function Envelope({ values }: { values: number[] }) {
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = Math.max(1, max - min)
  const step = 100 / values.length
  const path = values.map((value, index) => {
    const x = index * step
    const y = 48 - ((value - min) / span) * 40
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)} ${y.toFixed(2)}`
  }).join(' ')
  return (
    <svg viewBox="0 0 100 48" className="spark spark-large" role="img" aria-label="Acoustic envelope in dBFS">
      <path d={path} fill="none" stroke="#2563eb" strokeWidth="1.2" />
    </svg>
  )
}
