import type { OperationsSnapshot } from '../../types/operations'
import { panelState } from '../live/format'
import DetailDialog, { FactGrid } from './DetailDialog'

export default function VibrationDetailDialog({
  open,
  snapshot,
  onClose,
}: {
  open: boolean
  snapshot: OperationsSnapshot | null
  onClose: () => void
}) {
  const piezo = snapshot?.piezo
  return (
    <DetailDialog open={open} onClose={onClose} title="Piezo contact" state={panelState(piezo?.source_mode)}>
      <FactGrid
        rows={[
          ['Peak', piezo ? `${piezo.peak_adc_counts} ${piezo.unit}` : '—'],
          ['RMS', piezo ? `${piezo.rms_adc_counts} ${piezo.unit}` : '—'],
          ['Contact', piezo?.contact_state ?? 'No contact sample'],
          ['Site', piezo?.site_id ?? '—'],
          ['Clipped', piezo ? (piezo.clipped ? 'yes' : 'no') : '—'],
          ['Acceleration', 'not measured'],
          ['Source', piezo?.source_mode ?? 'unavailable'],
        ]}
      />
      <p className="quiet-line">The inventory has one piezo disk, assigned as a stationary surface-contact receiver. It is not a second buried reference and it is not an accelerometer. Counts are not g.</p>
      <p className="quiet-line">Couple the disk to the plywood at a stop, with a protective layer and a conditioned ADC input. A loose disk on the chassis is not a sand measurement. The snapshot has no ADC time series until a driver sends one.</p>
    </DetailDialog>
  )
}
