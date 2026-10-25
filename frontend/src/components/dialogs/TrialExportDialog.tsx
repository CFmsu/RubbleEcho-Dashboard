import { useState } from 'react'
import { downloadExport } from '../../api/operations'
import type { ActionRunner } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import DetailDialog from './DetailDialog'

export default function TrialExportDialog({
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
  const [format, setFormat] = useState<'zip' | 'json' | 'csv'>('zip')
  const [result, setResult] = useState('')
  const trialId = snapshot?.trial_id

  return (
    <DetailDialog open={open} onClose={onClose} title="Export trial" state={trialId ? snapshot?.badge : 'EMPTY'} dismissOnBackdrop>
      <p className="quiet-line">Trial {trialId ?? 'none'} · {snapshot?.mode ?? 'unavailable'} · geometry {snapshot?.geometry_revision ?? '—'}</p>
      <fieldset className="format-set">
        <legend>Format</legend>
        {(['zip', 'json', 'csv'] as const).map((item) => (
          <label key={item}>
            <input type="radio" name="export-format" checked={format === item} onChange={() => setFormat(item)} />
            {item.toUpperCase()}
          </label>
        ))}
      </fieldset>
      <label className="check-line">
        <input type="checkbox" checked={snapshot?.mode === 'simulation'} readOnly disabled={snapshot?.mode !== 'simulation'} /> Include images
      </label>
      <label className="check-line">
        <input type="checkbox" checked={snapshot?.mode === 'simulation'} readOnly disabled={snapshot?.mode !== 'simulation'} /> Include audio clips
      </label>
      <button
        type="button"
        className="btn primary"
        disabled={!trialId}
        onClick={() => {
          if (!trialId) return
          void run(async () => {
            await downloadExport(trialId, format)
            return `Downloaded ${trialId}.${format}`
          }).then((message) => setResult(message ?? '')).catch((caught: unknown) => {
            setResult(caught instanceof Error ? caught.message : 'Export failed')
          })
        }}
      >
        Download
      </button>
      {result ? <p role="status">{result}</p> : null}
      <p className="quiet-line">ZIP contains manifest.json, events.jsonl, measurements.csv, inference.jsonl, and README.txt. A simulation trial also includes the camera PNG and audio WAV for each visited point. Secrets are not included.</p>
    </DetailDialog>
  )
}
