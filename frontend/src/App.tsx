import { useEffect, useState } from 'react'
import About from './components/About'
import HowItWorks from './components/HowItWorks'
import DiagnosticsPage from './features/diagnostics/DiagnosticsPage'
import HeatmapPage from './features/heatmap/HeatmapPage'
import LegacyPanel from './features/operations/LegacyPanel'
import ReasoningPage from './features/reasoning/ReasoningPage'
import SensorsPage from './features/sensors/SensorsPage'
import { sendEstop } from './api/operations'
import { useOperations } from './hooks/useOperations'
import LiveOperations from './pages/LiveOperations'
import { Architecture } from './pages/Architecture'

type Page = 'live' | 'sensors' | 'heatmap' | 'reasoning' | 'diagnostics' | 'how' | 'about' | 'architecture' | 'legacy'

const NAV: Array<{ id: Page; label: string }> = [
  { id: 'live', label: 'Live Operations' },
  { id: 'sensors', label: 'Sensors' },
  { id: 'heatmap', label: 'Heatmap & Trials' },
  { id: 'reasoning', label: 'AI Reasoning' },
  { id: 'diagnostics', label: 'Diagnostics' },
]

export default function App() {
  const [page, setPage] = useState<Page>('live')
  const [helpOpen, setHelpOpen] = useState(false)
  const { snapshot, connection } = useOperations()
  const connected = connection === 'connected'
  const live = page === 'live'

  const openHelp = (next: Page) => {
    setHelpOpen(false)
    setPage(next)
  }

  return (
    <div className={live ? 'app-shell is-live' : 'app-shell is-page'} data-testid={live ? 'app-shell' : undefined}>
      <header className="app-header">
        <div className="brand">
          <h1>RubbleEcho</h1>
          <span>Sand table Rev C</span>
        </div>
        <nav className="primary-nav" aria-label="Main navigation">
          {NAV.map((item) => (
            <button key={item.id} type="button" aria-current={page === item.id ? 'page' : undefined} onClick={() => setPage(item.id)}>
              {item.label}
            </button>
          ))}
        </nav>
        <div className="header-tools">
          <Health snapshotLive={Boolean(snapshot?.system_live)} safety={snapshot?.safety_state} connected={connected} />
          <span className="mode-badge">{snapshot?.badge ?? 'DISCONNECTED'}</span>
          <Clock iso={snapshot?.updated_at_utc} />
          <details className="help-menu" open={helpOpen} onToggle={(event) => setHelpOpen(event.currentTarget.open)}>
            <summary>Help</summary>
            <div className="help-pop">
              <button type="button" onClick={() => openHelp('about')}>About</button>
              <button type="button" onClick={() => openHelp('how')}>How it works</button>
              <button type="button" onClick={() => openHelp('architecture')}>Architecture</button>
              <button type="button" onClick={() => openHelp('legacy')}>Legacy simulation</button>
            </div>
          </details>
          <HeaderStop connected={connected} />
        </div>
      </header>
      {live ? <LiveOperations snapshot={snapshot} connected={connected} /> : (
        <main className="page-scroll">
          {page === 'sensors' ? <SensorsPage snapshot={snapshot} /> : null}
          {page === 'heatmap' ? <HeatmapPage snapshot={snapshot} /> : null}
          {page === 'reasoning' ? <ReasoningPage snapshot={snapshot} /> : null}
          {page === 'diagnostics' ? <DiagnosticsPage snapshot={snapshot} /> : null}
          {page === 'how' ? <HowItWorks /> : null}
          {page === 'about' ? <About /> : null}
          {page === 'architecture' ? <Architecture /> : null}
          {page === 'legacy' ? <LegacyPanel startOpen /> : null}
        </main>
      )}
    </div>
  )
}

function Health({
  snapshotLive,
  safety,
  connected,
}: {
  snapshotLive: boolean
  safety: string | undefined
  connected: boolean
}) {
  const estop = safety === 'ESTOP'
  const kind = !connected ? 'hold' : estop ? 'estop' : snapshotLive ? 'ok' : 'idle'
  const label = !connected ? 'API down' : estop ? 'ESTOP' : snapshotLive ? 'Healthy' : 'Idle'
  return <span className="health" data-kind={kind}>{label}</span>
}

function Clock({ iso }: { iso: string | undefined }) {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(id)
  }, [])
  const label = now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  return <time className="clock" dateTime={iso ?? now.toISOString()} title={iso ? `Snapshot ${iso}` : 'No snapshot'}>{label}</time>
}

function HeaderStop({ connected }: { connected: boolean }) {
  const [failed, setFailed] = useState(false)
  return (
    <button
      type="button"
      className="stop-btn"
      disabled={!connected}
      title={failed ? 'Stop request failed' : connected ? 'Software stop. A hardware e-stop still cuts power.' : 'Safety controller unreachable'}
      onClick={() => {
        sendEstop().then(() => setFailed(false)).catch(() => setFailed(true))
      }}
    >
      STOP
    </button>
  )
}
