import type { OperationsSnapshot } from '../../types/operations'

function textValue(value: number | boolean | null | undefined, suffix = ''): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return `${value}${suffix}`
}

export default function RadarScope({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const radar = snapshot?.radar ?? null
  const paused = !radar || radar.stale || radar.source_mode === 'unavailable' || snapshot?.badge === 'DISCONNECTED'
  const presence = radar ? textValue(radar.human_presence) : 'Unknown'

  return (
    <section className="ops-card">
      <h2 className="text-xl font-semibold">60 GHz radar</h2>
      <div className={`radar-stage mt-3 ${paused ? 'is-paused' : ''}`} aria-hidden="true">
        <div className="radar-disc" />
        <div className="radar-ring" style={{ width: 260, height: 260 }} />
        <div className="radar-ring" style={{ width: 180, height: 180 }} />
        <div className="radar-ring" style={{ width: 100, height: 100 }} />
        <div className="radar-pivot"><div className="radar-beam" /></div>
      </div>
      <p className="mt-2 text-xs text-slate-500">Illustrative beam animation — real values shown separately. Visual sweep: illustrative.</p>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div><dt className="text-slate-500">Human presence</dt><dd>{presence}</dd></div>
        <div><dt className="text-slate-500">Distance</dt><dd>{radar?.distance_m ?? '—'}{radar?.distance_m != null ? ' m' : ''}</dd></div>
        <div><dt className="text-slate-500">Breathing</dt><dd>{radar?.breath_rate_bpm ?? '—'}{radar?.breath_rate_bpm != null ? ' breaths/min' : ''}</dd></div>
        <div><dt className="text-slate-500">Heart rate</dt><dd>{radar?.heart_rate_bpm ?? '—'}{radar?.heart_rate_bpm != null ? ' bpm' : ''}</dd></div>
        <div><dt className="text-slate-500">Phase</dt><dd>{radar?.total_phase ?? '—'}{radar?.total_phase != null ? ' raw' : ''}</dd></div>
        <div><dt className="text-slate-500">Stability</dt><dd>{radar?.stability ?? '—'}</dd></div>
      </dl>
      <p className="mt-2 text-xs">Firmware {radar?.firmware ?? '—'} · last sample {radar?.captured_at_utc ?? '—'} · source {radar?.source_mode ?? 'unavailable'}</p>
      <p className="mt-1 text-xs text-slate-500">
        {radar?.target_xy_m && radar.spatial_coordinates_used
          ? `Firmware XY ${radar.target_xy_m.join(', ')} m. Calibration is unverified.`
          : 'No spatial target is drawn. Presence and range stay on the center line.'}
      </p>
      <p className="mt-2 text-xs" title="Red would mark a thresholded sensor event, not a confirmed living person. Yellow is tentative. Gray is stale.">
        Legend: green beam is the illustration. Red is not a confirmed person. Gray means stale or disconnected.
      </p>
      {radar?.notes?.length ? <p className="mt-1 text-xs text-amber-700">{radar.notes.join(' · ')}</p> : null}
    </section>
  )
}
