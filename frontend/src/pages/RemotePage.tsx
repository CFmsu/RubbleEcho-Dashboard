import { useEffect, useRef, useState } from 'react'
import { startHardware } from '../api/operations'

type Sensors = Record<string, boolean>
type RemoteState = {
  mode?: 'stopped' | 'manual' | 'auto'
  step?: string | null
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
  { id: 'camera', label: 'Camera' },
  { id: 'acoustic', label: 'Mic' },
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
  const [note, setNote] = useState('Stopped at the first square. Hold an arrow to drive.')
  const heldCommand = useRef<string | null>(null)
  const modeRef = useRef<RemoteState['mode']>('stopped')
  const repeatTimer = useRef<number | null>(null)
  const pending = useRef<string | null>(null)
  const sending = useRef(false)

  useEffect(() => {
    let stop = false
    const pull = () => {
      fetch('/api/remote')
        .then((response) => response.json())
        .then((body: RemoteState) => {
          if (stop) return
          setRemote(body)
          modeRef.current = body.mode
          if (body.mode === 'auto' && body.step && body.step !== 'done' && !heldCommand.current) {
            const label = SENSORS.find((item) => item.id === body.step)?.label
            setNote(body.step === 'model' ? 'Sending the sound to the model.' : `${label ?? body.step} is on. The rover is stopped.`)
          }
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

  const pump = () => {
    if (sending.current) return
    const command = pending.current
    if (!command) return
    pending.current = null
    sending.current = true
    fetch('/api/remote/drive', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command }),
    })
      .then((response) => response.json())
      .then((body: { rover?: { sent?: boolean; reason?: string } }) => {
        if (body.rover?.sent) setNote(command === 'S' ? 'Stopped' : 'Moving')
        else if (body.rover?.reason === 'auto_sampling') setNote('Auto is sampling. Switch to Manual to drive.')
        else if (body.rover?.reason === 'rover_not_found' || body.rover?.reason === 'not_sent') setNote('Rover not connected')
        else if (command === 'S') setNote('Stopped')
        else setNote('Did not reach the rover')
      })
      .catch(() => setNote('Drive request failed'))
      .finally(() => {
        sending.current = false
        pump()
      })
  }

  const enqueue = (command: string) => {
    pending.current = command
    pump()
  }

  const stopRepeat = () => {
    if (repeatTimer.current !== null) {
      window.clearInterval(repeatTimer.current)
      repeatTimer.current = null
    }
  }

  const release = (command: string) => {
    if (heldCommand.current !== command) return
    heldCommand.current = null
    stopRepeat()
    setHeld(null)
    enqueue('S')
  }

  const hold = (command: string, event: React.PointerEvent<HTMLButtonElement>) => {
    event.preventDefault()
    if (command !== 'S' && modeRef.current === 'auto') {
      setNote('Auto is sampling. Switch to Manual to drive.')
      return
    }
    if (command === 'S') {
      heldCommand.current = null
      stopRepeat()
      setHeld('S')
      enqueue('S')
      window.setTimeout(() => setHeld((current) => (current === 'S' ? null : current)), 160)
      return
    }
    if (heldCommand.current === command) return
    if (heldCommand.current) {
      stopRepeat()
      enqueue('S')
    }
    heldCommand.current = command
    event.currentTarget.setPointerCapture(event.pointerId)
    setHeld(command)
    enqueue(command)
    repeatTimer.current = window.setInterval(() => {
      if (heldCommand.current === command) enqueue(command)
    }, 250)
  }

  const chooseMode = (mode: 'auto' | 'manual') => {
    fetch('/api/remote/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    })
      .then((response) => response.json())
      .then((body: RemoteState) => {
        setRemote((current) => ({ ...current, ...body }))
        modeRef.current = body.mode
        setNote(mode === 'manual' ? 'Manual. Hold an arrow. The rover starts stopped.' : 'Auto selected. Arm to sample. The rover stays stopped.')
      })
      .catch(() => setNote('Mode switch failed'))
  }

  const arm = () => {
    setHeld('start')
    startHardware()
      .then((message) => setNote(message))
      .catch(() => setNote('Arm did not reach the laptop'))
      .finally(() => setHeld(null))
  }

  const mode = remote.mode ?? 'stopped'

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
            onPointerDown={(event) => hold(item.command, event)}
            onPointerUp={(event) => {
              event.preventDefault()
              release(item.command)
            }}
            onPointerCancel={() => release(item.command)}
            onLostPointerCapture={() => release(item.command)}
            onContextMenu={(event) => event.preventDefault()}
          >
            <Chevron place={item.place} />
          </button>
        ))}
      </div>
      <div className="remote-actions">
        <button type="button" className={held === 'start' ? 'remote-start is-held' : 'remote-start'} onClick={arm}>
          Arm
        </button>
        <button
          type="button"
          className={held === 'S' ? 'remote-stop is-held' : 'remote-stop'}
          onPointerDown={(event) => hold('S', event)}
        >
          Stop
        </button>
      </div>
      <p className="remote-note" role="status">{note}</p>
      <div className="remote-sensors">
        <div className="remote-radio" role="radiogroup" aria-label="Drive mode">
          <span>Drive</span>
          <label>
            <input type="radio" name="drive-mode" checked={mode === 'auto'} onChange={() => chooseMode('auto')} />
            Auto
          </label>
          <label>
            <input type="radio" name="drive-mode" checked={mode === 'manual'} onChange={() => chooseMode('manual')} />
            Manual
          </label>
        </div>
      </div>
    </section>
  )
}
