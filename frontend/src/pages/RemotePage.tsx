import { useEffect, useRef, useState } from 'react'

type RemoteState = {
  mode?: 'stopped' | 'manual' | 'auto'
  step?: string | null
  speed?: number
  last?: { command?: string | null; sent?: boolean; reason?: string | null; port?: string | null }
}

const PAD = [
  { command: 'F', place: 'up' as const },
  { command: 'L', place: 'left' as const },
  { command: 'R', place: 'right' as const },
  { command: 'B', place: 'down' as const },
]

function Chevron({ place }: { place: 'up' | 'left' | 'right' | 'down' }) {
  const turn = { up: 0, right: 90, down: 180, left: 270 }[place]
  return (
    <svg viewBox="0 0 24 24" width="34" height="34" aria-hidden="true" style={{ transform: `rotate(${turn}deg)` }}>
      <path d="M5 14.5 12 7.5 19 14.5" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function postJson(url: string, body: unknown) {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export default function RemotePage({ onDashboard }: { onDashboard: () => void }) {
  const [remote, setRemote] = useState<RemoteState>({})
  const [held, setHeld] = useState<string | null>(null)
  const [motorSpeed, setMotorSpeed] = useState(9)
  const [ultraSpeed, setUltraSpeed] = useState(3)
  const [waveSpeed, setWaveSpeed] = useState(3)
  const [note, setNote] = useState('Hold an arrow to drive. Release sends stop.')
  const heldCommand = useRef<string | null>(null)
  const modeRef = useRef<RemoteState['mode']>('stopped')
  const motorSpeedRef = useRef(9)
  const ultraSpeedRef = useRef(3)
  const waveSpeedRef = useRef(3)
  const repeatTimer = useRef<number | null>(null)
  const servoTimer = useRef<number | null>(null)
  const heldServo = useRef<string | null>(null)
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
    postJson('/api/remote/drive', { command })
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
    const level = motorSpeedRef.current
    postJson('/api/remote/speed', { level }).finally(() => {
      if (heldCommand.current !== command) return
      enqueue(command)
      repeatTimer.current = window.setInterval(() => {
        if (heldCommand.current === command) enqueue(command)
      }, 250)
    })
  }

  const stopServoRepeat = () => {
    if (servoTimer.current !== null) {
      window.clearInterval(servoTimer.current)
      servoTimer.current = null
    }
  }

  const sendServo = (horn: 'ultrasonic' | 'mmwave', move: 'left' | 'right' | 'center' | 'stop') => {
    const speed = horn === 'ultrasonic' ? ultraSpeedRef.current : waveSpeedRef.current
    postJson('/api/remote/servo', { horn, move, speed }).catch(() => setNote('Servo request failed'))
  }

  const releaseServo = (horn: 'ultrasonic' | 'mmwave', move: 'left' | 'right' | 'center') => {
    const key = `${horn}-${move}`
    if (heldServo.current !== key) return
    heldServo.current = null
    stopServoRepeat()
    setHeld(null)
    sendServo(horn, 'stop')
    setNote(horn === 'ultrasonic' ? 'Ultrasonic servo released' : 'mmWave servo released')
  }

  const holdServo = (horn: 'ultrasonic' | 'mmwave', move: 'left' | 'right' | 'center', event: React.PointerEvent<HTMLButtonElement>) => {
    event.preventDefault()
    const key = `${horn}-${move}`
    if (heldServo.current === key) return
    if (heldServo.current) {
      stopServoRepeat()
      const [previousHorn] = heldServo.current.split('-') as ['ultrasonic' | 'mmwave']
      sendServo(previousHorn, 'stop')
    }
    heldServo.current = key
    event.currentTarget.setPointerCapture(event.pointerId)
    setHeld(key)
    sendServo(horn, move)
    setNote(horn === 'ultrasonic' ? 'Turning the ultrasonic servo' : 'Turning the mmWave servo')
    servoTimer.current = window.setInterval(() => {
      if (heldServo.current === key) sendServo(horn, move)
    }, 180)
  }

  const chooseMode = (mode: 'auto' | 'manual') => {
    postJson('/api/remote/mode', { mode })
      .then((response) => response.json())
      .then((body: RemoteState) => {
        setRemote((current) => ({ ...current, ...body }))
        modeRef.current = body.mode
        setNote(mode === 'manual' ? 'Manual. Hold an arrow. Release sends stop.' : 'Auto selected. The rover stays stopped until it is armed.')
      })
      .catch(() => setNote('Mode switch failed'))
  }

  const changeMotorSpeed = (level: number) => {
    motorSpeedRef.current = level
    setMotorSpeed(level)
    postJson('/api/remote/speed', { level })
      .then(() => setNote(`Motor speed ${level}`))
      .catch(() => setNote('Speed request failed'))
  }

  const runJob = (kind: 'deploy' | 'collect') => {
    setNote(kind === 'deploy' ? 'Deploy sent. Recording for 12 seconds. The rover is not driven.' : 'Collect signal sent. Saving ultrasonic, radar, and microphone.')
    fetch(`/api/remote/${kind}`, { method: 'POST' }).catch(() => setNote(kind === 'deploy' ? 'Deploy request failed' : 'Collect request failed'))
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
      <p className="remote-note" role="status">{note} Letting go stops that control.</p>
      <div className="remote-block">
        <h2>Motor speed</h2>
        <label className="remote-speed">
          <span>{motorSpeed}</span>
          <input
            type="range"
            min={0}
            max={9}
            step={1}
            value={motorSpeed}
            aria-label="Motor speed"
            onChange={(event) => changeMotorSpeed(Number(event.target.value))}
          />
        </label>
      </div>
      <div className="remote-block">
        <h2>Ultrasonic servo</h2>
        <div className="remote-row">
          <button
            type="button"
            className={held === 'ultrasonic-left' ? 'is-held' : undefined}
            onPointerDown={(event) => holdServo('ultrasonic', 'left', event)}
            onPointerUp={() => releaseServo('ultrasonic', 'left')}
            onPointerCancel={() => releaseServo('ultrasonic', 'left')}
            onLostPointerCapture={() => releaseServo('ultrasonic', 'left')}
          >
            Left
          </button>
          <button
            type="button"
            className={held === 'ultrasonic-center' ? 'is-held' : undefined}
            onPointerDown={(event) => holdServo('ultrasonic', 'center', event)}
            onPointerUp={() => releaseServo('ultrasonic', 'center')}
            onPointerCancel={() => releaseServo('ultrasonic', 'center')}
            onLostPointerCapture={() => releaseServo('ultrasonic', 'center')}
          >
            Center
          </button>
          <button
            type="button"
            className={held === 'ultrasonic-right' ? 'is-held' : undefined}
            onPointerDown={(event) => holdServo('ultrasonic', 'right', event)}
            onPointerUp={() => releaseServo('ultrasonic', 'right')}
            onPointerCancel={() => releaseServo('ultrasonic', 'right')}
            onLostPointerCapture={() => releaseServo('ultrasonic', 'right')}
          >
            Right
          </button>
        </div>
        <label className="remote-speed">
          <span>Speed {ultraSpeed}</span>
          <input
            type="range"
            min={1}
            max={9}
            step={1}
            value={ultraSpeed}
            aria-label="Ultrasonic servo speed"
            onChange={(event) => {
              const level = Number(event.target.value)
              ultraSpeedRef.current = level
              setUltraSpeed(level)
            }}
          />
        </label>
      </div>
      <div className="remote-block">
        <h2>mmWave servo</h2>
        <div className="remote-row">
          <button
            type="button"
            className={held === 'mmwave-left' ? 'is-held' : undefined}
            onPointerDown={(event) => holdServo('mmwave', 'left', event)}
            onPointerUp={() => releaseServo('mmwave', 'left')}
            onPointerCancel={() => releaseServo('mmwave', 'left')}
            onLostPointerCapture={() => releaseServo('mmwave', 'left')}
          >
            Left
          </button>
          <button
            type="button"
            className={held === 'mmwave-center' ? 'is-held' : undefined}
            onPointerDown={(event) => holdServo('mmwave', 'center', event)}
            onPointerUp={() => releaseServo('mmwave', 'center')}
            onPointerCancel={() => releaseServo('mmwave', 'center')}
            onLostPointerCapture={() => releaseServo('mmwave', 'center')}
          >
            Center
          </button>
          <button
            type="button"
            className={held === 'mmwave-right' ? 'is-held' : undefined}
            onPointerDown={(event) => holdServo('mmwave', 'right', event)}
            onPointerUp={() => releaseServo('mmwave', 'right')}
            onPointerCancel={() => releaseServo('mmwave', 'right')}
            onLostPointerCapture={() => releaseServo('mmwave', 'right')}
          >
            Right
          </button>
        </div>
        <label className="remote-speed">
          <span>Speed {waveSpeed}</span>
          <input
            type="range"
            min={1}
            max={9}
            step={1}
            value={waveSpeed}
            aria-label="mmWave servo speed"
            onChange={(event) => {
              const level = Number(event.target.value)
              waveSpeedRef.current = level
              setWaveSpeed(level)
            }}
          />
        </label>
      </div>
      <div className="remote-row" style={{ width: 'min(100%, 360px)' }}>
        <button type="button" className="remote-job" onClick={() => runJob('deploy')}>Deploy</button>
        <button type="button" className="remote-job collect" onClick={() => runJob('collect')}>Collect signal</button>
      </div>
      <div className="remote-sensors">
        <div className="remote-radio" role="radiogroup" aria-label="Drive mode">
          <span>Drive</span>
          <label>
            <input type="radio" name="drive-mode" checked={mode === 'auto'} onChange={() => chooseMode('auto')} />
            Auto
          </label>
          <label>
            <input type="radio" name="drive-mode" checked={mode === 'manual' || mode === 'stopped'} onChange={() => chooseMode('manual')} />
            Manual
          </label>
        </div>
      </div>
    </section>
  )
}
