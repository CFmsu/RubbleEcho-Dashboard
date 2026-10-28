import { useEffect, useState } from 'react'

type Sensors = Record<string, boolean>
type RemoteState = {
  last?: { command?: string | null; sent?: boolean; reason?: string | null; port?: string | null }
  sensors?: Sensors
}

const PAD = [
  { command: 'F', place: 'up' as const },
  { command: 'L', place: 'left' as const },
  { command: 'R', place: 'right' as const },
  { command: 'B', place: 'down' as const },
]

const SENSORS = [
  { id: 'radar', label: 'Radar' },
  { id: 'ultrasonic', label: 'Range' },
  { id: 'acoustic', label: 'Mic' },
  { id: 'camera', label: 'Cam' },
]

function Chevron({ place }: { place: 'up' | 'left' | 'right' | 'down' }) {
  const turn = { up: 0, right: 90, down: 180, left: 270 }[place]
  return (
    <svg viewBox="0 0 24 24" width="34" height="34" aria-hidden="true" style={{ transform: `rotate(${turn}deg)` }}>
      <path d="M5 14.5 12 7.5 19 14.5" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function RemotePage({ onDashboard }: { onDashboard: () => void }) {
  const [remote, setRemote] = useState<RemoteState>({})
  const [held, setHeld] = useState<string | null>(null)
  const [note, setNote] = useState('Hold an arrow')

  useEffect(() => {
    let stop = false
    const pull = () => {
      fetch('/api/remote')
        .then((response) => response.json())
        .then((body: RemoteState) => {
          if (!stop) setRemote(body)
        })
        .catch(() => {
          if (!stop) setNote('Dashboard API is not reachable.')
        })
    }
    pull()
    const timer = window.setInterval(pull, 1000)
    return () => {
      stop = true
      window.clearInterval(timer)
    }
  }, [])

  const drive = (command: string) => {
    fetch('/api/remote/drive', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command }),
    })
      .then((response) => response.json())
      .then((body: { rover?: { sent?: boolean; reason?: string } }) => {
        if (body.rover?.sent) setNote(command === 'S' ? 'Stopped' : 'Moving')
        else if (body.rover?.reason === 'rover_not_found' || body.rover?.reason === 'not_sent') setNote('Rover not connected')
        else if (command === 'S') setNote('Stopped')
        else setNote('Did not reach the rover')
      })
      .catch(() => setNote('Drive request failed'))
  }

  const hold = (command: string) => {
    setHeld(command)
    if (command === 'S') {
      drive('S')
      window.setTimeout(() => setHeld(null), 160)
      return
    }
    drive(command)
    const timer = window.setInterval(() => drive(command), 400)
    const release = () => {
      window.clearInterval(timer)
      setHeld(null)
      drive('S')
      window.removeEventListener('pointerup', release)
      window.removeEventListener('pointercancel', release)
    }
    window.addEventListener('pointerup', release)
    window.addEventListener('pointercancel', release)
  }

  const toggle = (sensor: string, enabled: boolean) => {
    fetch('/api/remote/sensor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sensor, enabled }),
    })
      .then((response) => response.json())
      .then((body: { sensors?: Sensors }) => {
        if (body.sensors) setRemote((current) => ({ ...current, sensors: body.sensors }))
      })
      .catch(() => setNote('Sensor switch failed'))
  }

  const startSession = () => {
    setHeld('start')
    fetch('/api/mission/live', { method: 'POST' })
      .then((response) => {
        if (!response.ok) throw new Error('start failed')
        setNote('Session open on this laptop. The car did not move.')
      })
      .catch(() => setNote('Start did not reach the laptop'))
      .finally(() => setHeld(null))
  }

  const sensors = remote.sensors ?? {}

  return (
    <section className="remote-pad">
      <button type="button" className="remote-back" onClick={onDashboard}>Dashboard</button>
      <div className="remote-cross">
        {PAD.map((item) => (
          <button
            key={item.command}
            type="button"
            data-place={item.place}
            aria-label={item.place}
            className={held === item.command ? 'remote-key is-held' : 'remote-key'}
            onPointerDown={(event) => {
              event.preventDefault()
              hold(item.command)
            }}
            onContextMenu={(event) => event.preventDefault()}
          >
            <Chevron place={item.place} />
          </button>
        ))}
      </div>
      <div className="remote-actions">
        <button type="button" className={held === 'start' ? 'remote-start is-held' : 'remote-start'} onClick={startSession}>
          Start
        </button>
        <button
          type="button"
          className={held === 'S' ? 'remote-stop is-held' : 'remote-stop'}
          onPointerDown={(event) => {
            event.preventDefault()
            hold('S')
          }}
        >
          Stop
        </button>
      </div>
      <p className="remote-note" role="status">{note}</p>
      <div className="remote-sensors">
        {SENSORS.map(({ id, label }) => {
          const on = sensors[id] !== false
          return (
            <div key={id} className="remote-radio" role="radiogroup" aria-label={label}>
              <span>{label}</span>
              <label>
                <input type="radio" name={id} checked={on} onChange={() => toggle(id, true)} />
                On
              </label>
              <label>
                <input type="radio" name={id} checked={!on} onChange={() => toggle(id, false)} />
                Off
              </label>
            </div>
          )
        })}
      </div>
    </section>
  )
}
