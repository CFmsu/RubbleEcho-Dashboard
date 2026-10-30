import { useMemo, useState } from 'react'
import SandTableFigure from '../../components/live/SandTableFigure'
import { useGeometry } from '../../hooks/useGeometry'
import type { OperationsSnapshot } from '../../types/operations'

type CellRow = {
  id: string
  score: number | null
  sound: string
  radar: string
  range: string
  ultrasonic: string
}

function classFrom(summary: string | undefined): string {
  const match = summary?.match(/class ([a-z/]+)/i)
  return match?.[1] ?? ''
}

function cellRows(snapshot: OperationsSnapshot): CellRow[] {
  const rows = snapshot.heatmap_points
    .filter((point) => point.sample_count > 0)
    .map((point) => {
      const readings = point.readings
      const acoustic = snapshot.events.find((event) => event.site_id === point.point_id && event.sensor === 'acoustic')
      const radarEvent = snapshot.events.find((event) => event.site_id === point.point_id && event.sensor === 'radar')
      const ultra = snapshot.events.find((event) => event.site_id === point.point_id && event.sensor === 'ultrasonic')
      const presence = readings?.radar_presence
      const radarText = radarEvent?.summary ?? ''
      const distance = readings?.distance_m
      const rangeMatch = radarText.match(/distance ([\d.]+) m/)
      const ultraMatch = ultra?.summary?.match(/([\d.]+)\s*cm/)
      const radar = presence === true || /:\s*present/.test(radarText)
        ? 'presence reported'
        : presence === false || radarText.includes('no person')
          ? 'no presence'
          : radarText ? 'radar row' : 'no radar row'
      return {
        id: point.point_id,
        score: point.score,
        sound: plainSound(readings?.sound || classFrom(acoustic?.summary) || ''),
        radar: plainRadar(radar),
        range: typeof distance === 'number' ? `${distance.toFixed(2)} m` : rangeMatch ? `${rangeMatch[1]} m` : '',
        ultrasonic: typeof readings?.ultrasonic_cm === 'number' ? `${readings.ultrasonic_cm.toFixed(1)} cm` : ultraMatch ? `${ultraMatch[1]} cm` : '',
      }
    })
  if (snapshot.reasoning?.ranking_allowed === true) {
    rows.sort((left, right) => (right.score ?? -1) - (left.score ?? -1))
  }
  return rows
}

function plainSound(value: string): string {
  if (value === 'knock') return 'a knock'
  if (value.includes('scratch')) return 'a scrape'
  if (value === 'ambient' || value === 'silence') return 'only the room'
  if (!value || value === 'no sound row') return 'no clear sound'
  return value
}

function plainRadar(value: string): string {
  if (value === 'presence reported') return 'radar presence flag set'
  if (value === 'no presence') return 'radar presence flag clear'
  return 'no radar flag'
}

function spoken(snapshot: OperationsSnapshot, ranked: CellRow[]): string {
  const narrative = snapshot.reasoning?.narrative?.trim()
  const lead = ranked[0]
  const second = ranked[1]
  if (snapshot.reasoning?.ranking_allowed !== true && snapshot.reasoning?.sufficiency_reason) {
    const note = snapshot.reasoning.audio_note ? ` ${snapshot.reasoning.audio_note}` : ''
    return `${snapshot.reasoning.sufficiency_reason}${note}`
  }
  if (narrative && (!lead || narrative.includes(lead.id))) {
    if (snapshot.reasoning?.ranking_allowed !== true) return narrative
    if (second && !narrative.includes(second.id)) {
      const kept = narrative
        .split(/(?<=\.)\s+/)
        .filter((sentence) => !ranked.some((row, index) => index > 0 && sentence.includes(row.id)))
        .join(' ')
        .replace(/\.\s*$/, '')
      return `${kept || narrative.replace(/\.\s*$/, '')}. After that, look at ${second.id}.`
    }
    return narrative
  }
  if (!lead) return 'No completed observations yet. Start a scan to collect evidence.'
  if (snapshot.reasoning?.ranking_allowed === false) {
    return snapshot.reasoning.sufficiency_reason || 'These readings do not distinguish a next square.'
  }
  const follow = second && snapshot.reasoning?.ranking_allowed ? ` After that, look at ${second.id}.` : ''
  const audio = snapshot.reasoning?.audio_note ? ` ${snapshot.reasoning.audio_note}` : ''
  return `Check ${lead.id} first. Ultrasonic and radar notes: ${lead.radar}.${lead.ultrasonic ? ` Obstacle distance ${lead.ultrasonic}.` : ''}${follow}${audio}`
}

export default function ReasoningPage({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const { geometry, error } = useGeometry()
  const ranked = useMemo(() => (snapshot ? cellRows(snapshot) : []), [snapshot])
  const named = snapshot?.reasoning?.recommendation.point_id
  const lead = named && ranked.some((row) => row.id === named) ? named : ranked[0]?.id ?? ''
  const [picked, setPicked] = useState<string | null>(null)
  const selected = picked && ranked.some((row) => row.id === picked) ? picked : lead

  const advice = snapshot ? spoken(snapshot, ranked) : 'Waiting for the console.'
  const sampled = ranked.length
  const totalSquares = snapshot?.scan_route?.length || sampled

  return (
    <div className="search-board">
      <header className="search-head">
        <div>
          <h2>Where to check first</h2>
          <p>{advice}</p>
        </div>
        <div>
          <p className="search-note">This is for a person at the table. It does not move the rover, and it does not say someone is under the sand.</p>
          <a className="btn primary" href="/api/briefing.pdf">Download the briefing</a>
        </div>
      </header>

      <ol className="search-steps">
        <li>
          <span>1</span>
          <div>
            <strong>Observe</strong>
            <p>{sampled === 0 ? 'The rover visits each square of the 3 by 3 grid and records the sensors that are connected.' : `${sampled} of ${totalSquares} squares have a stored observation.`}</p>
          </div>
        </li>
        <li>
          <span>2</span>
          <div>
            <strong>Assess</strong>
            <p>After all nine squares, the assessment uses the stored readings, including the microphone.</p>
          </div>
        </li>
        <li>
          <span>3</span>
          <div>
            <strong>Review</strong>
            <p>The briefing names the next square to inspect only when the stored readings distinguish one. It does not confirm a person.</p>
          </div>
        </li>
      </ol>

      <div className="search-layout">
        <section className="search-map">
          {geometry ? (
            <SandTableFigure geometry={geometry} snapshot={snapshot} showBoxes selectedId={selected} onSelect={setPicked} />
          ) : (
            <p>{error || 'Loading the sand table.'}</p>
          )}
        </section>

        <section className="search-side">
          <h3>Check in this order</h3>
          {ranked.length === 0 ? <p className="search-empty">No completed observations yet. Start a scan to collect evidence.</p> : null}
          {snapshot?.reasoning?.ranking_allowed === false && ranked.length > 0 ? (
            <p className="search-empty">These readings do not distinguish a next square, so they are not ranked.</p>
          ) : null}
          <ol className="search-order">
            {ranked.map((row, index) => (
              <li key={row.id}>
                <button type="button" className={row.id === selected ? 'is-selected' : ''} onClick={() => setPicked(row.id)}>
                  <strong>{index + 1}. {row.id}</strong>
                  <span>{row.sound} · {row.radar}{row.range ? ` · about ${row.range} out` : ''}</span>
                  {row.ultrasonic ? <span>The wall was about {row.ultrasonic} ahead</span> : null}
                </button>
              </li>
            ))}
          </ol>
        </section>
      </div>

    </div>
  )
}
