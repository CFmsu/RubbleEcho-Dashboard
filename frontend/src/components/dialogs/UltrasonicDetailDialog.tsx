import { useEffect, useState } from 'react'
import type { OperationsSnapshot } from '../../types/operations'
import EchoDiagram from '../live/EchoDiagram'
import { panelState } from '../live/format'
import { noteRange, readRange, type RangeSample } from '../live/rangeTrace'
import DetailDialog, { FactGrid } from './DetailDialog'

export default function UltrasonicDetailDialog({
  open,
  snapshot,
  onClose,
}: {
  open: boolean
  snapshot: OperationsSnapshot | null
  onClose: () => void
}) {
  const range = snapshot?.ultrasonic
  const [values, setValues] = useState<RangeSample[]>(() => readRange().slice())
  useEffect(() => {
    if (!open) return
    const push = () => {
      noteRange(range?.distance_cm)
      setValues(readRange().slice())
    }
    push()
    const id = window.setInterval(push, 450)
    return () => window.clearInterval(id)
  }, [open, range?.distance_cm])

  const latest = values[values.length - 1]
  const peak = values.length ? Math.max(...values.map((item) => item.cm)) : null
  const floor = values.length ? Math.min(...values.map((item) => item.cm)) : null
  const recent = values.slice(-8).reverse()

  return (
    <DetailDialog open={open} onClose={onClose} title="HC-SR04 obstacle distance" state={panelState(range?.source_mode)}>
      <p className="measure">{range?.distance_cm == null ? '—' : range.distance_cm}<small> cm</small></p>
      <EchoDiagram distanceCm={range?.distance_cm ?? null} echoTimeout={Boolean(range?.echo_timeout)} />
      <p className="quiet-line">The violet point sits at the measured range and slides when the distance changes. Inside 20 cm the rover blocks the next grid cell, turns, and listens.</p>
      <table className="dialog-table">
        <thead>
          <tr>
            <th>Reading</th>
            <th>cm</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>Latest</td><td>{latest ? latest.cm.toFixed(1) : '—'}</td></tr>
          <tr><td>Closest in this trace</td><td>{floor == null ? '—' : floor.toFixed(1)}</td></tr>
          <tr><td>Farthest in this trace</td><td>{peak == null ? '—' : peak.toFixed(1)}</td></tr>
          {recent.map((item, index) => (
            <tr key={`${item.t}-${index}`}>
              <td>{index === 0 ? 'Now' : `${((latest?.t ?? item.t) - item.t) / 1000} s ago`.replace(/(\.\d)\d*/, '$1')}</td>
              <td>{item.cm.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <FactGrid
        rows={[
          ['Direction', range?.direction ?? '—'],
          ['Quality', range?.quality ?? 'no sample'],
          ['Echo timeout', range ? (range.echo_timeout ? 'yes — path is not clear' : 'no') : '—'],
          ['Source', range?.source_mode ?? 'unavailable'],
          ['Meaning', 'Obstacle range in front of the sensor. Not depth through rubble.'],
          ['Stop margin', 'Configured policy, initial 20 cm, pending a measured rover. Not a reading.'],
        ]}
      />
    </DetailDialog>
  )
}
