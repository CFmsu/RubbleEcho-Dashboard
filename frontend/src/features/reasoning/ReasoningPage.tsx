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
  return snapshot.heatmap_points
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
    .sort((left, right) => (right.score ?? -1) - (left.score ?? -1))
}

function plainSound(value: string): string {
  if (value === 'knock') return 'a knock'
  if (value.includes('scratch')) return 'a scrape'
  if (value === 'ambient' || value === 'silence') return 'only the room'
  if (!value || value === 'no sound row') return 'no clear sound'
  return value
}

function plainRadar(value: string): string {
  if (value === 'presence reported') return 'a pulse showed up'
  if (value === 'no presence') return 'no pulse'
  return 'no pulse reading'
}

function spoken(snapshot: OperationsSnapshot, ranked: CellRow[]): string {
  const narrative = snapshot.reasoning?.narrative?.trim()
  const lead = ranked[0]
  const second = ranked[1]
  if (narrative && (!lead || narrative.includes(lead.id))) {
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
  if (!lead) return 'The rover has not finished a stop yet. When it does, the briefing names the first square and includes the camera frame from that stop.'
  const follow = second ? ` After that, look at ${second.id}.` : ''
  return `Walk to ${lead.id} first. We heard ${lead.sound} there, and ${lead.radar}.${follow} Download the briefing for the camera frame from that stop.`
}

export default function ReasoningPage({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const { geometry, error } = useGeometry()
  const ranked = useMemo(() => (snapshot ? cellRows(snapshot) : []), [snapshot])
  const named = snapshot?.reasoning?.recommendation.point_id
  const lead = named && ranked.some((row) => row.id === named) ? named : ranked[0]?.id ?? ''
  const [picked, setPicked] = useState<string | null>(null)
  const selected = picked && ranked.some((row) => row.id === picked) ? picked : lead
  const [photoFailed, setPhotoFailed] = useState(false)
  const [photoPoint, setPhotoPoint] = useState(selected)
  if (photoPoint !== selected) {
    setPhotoPoint(selected)
    setPhotoFailed(false)
  }

  const advice = snapshot ? spoken(snapshot, ranked) : 'Waiting for the console.'
  const fallbackPhoto = snapshot?.cameras.find((camera) => camera.image_url)?.image_url ?? ''
  const photo = photoFailed ? fallbackPhoto : selected ? `/api/simulation/camera.png?point=${encodeURIComponent(selected)}` : fallbackPhoto
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
            <strong>Stop and listen</strong>
            <p>{sampled === 0 ? 'The rover stops in each square of the 3 by 3 grid and listens.' : `${sampled} of ${totalSquares} squares have been checked.`}</p>
          </div>
        </li>
        <li>
          <span>2</span>
          <div>
            <strong>Check for a pulse</strong>
            <p>After the sound, it checks whether a pulse showed up, then turns when the wall is close.</p>
          </div>
        </li>
        <li>
          <span>3</span>
          <div>
            <strong>Look at the frame</strong>
            <p>The briefing includes the camera frame from the square it asks you to walk to.</p>
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
          {ranked.length === 0 ? <p className="search-empty">The walk has not stored a cell yet.</p> : null}
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
          {photo ? (
            <figure>
              <img src={photo} alt={selected ? `Stored frame for ${selected}` : 'Stored frame'} onError={() => setPhotoFailed(true)} />
              <figcaption>{selected ? `Camera frame from ${selected}.` : 'Camera frame.'} This is the picture that goes on the briefing.</figcaption>
            </figure>
          ) : null}
        </section>
      </div>

    </div>
  )
}
