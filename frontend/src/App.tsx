import { useEffect, useState } from 'react'
import About from './components/About'
import HowItWorks from './components/HowItWorks'
import DiagnosticsPage from './features/diagnostics/DiagnosticsPage'
import HeatmapPage from './features/heatmap/HeatmapPage'
import LegacyPanel from './features/operations/LegacyPanel'
import ReasoningPage from './features/reasoning/ReasoningPage'
import SensorsPage from './features/sensors/SensorsPage'
import { sendEstop, startHardware } from './api/operations'
import { useOperations } from './hooks/useOperations'
import LiveOperations from './pages/LiveOperations'
import RemotePage from './pages/RemotePage'
import { Architecture } from './pages/Architecture'

type Page = 'mission' | 'assessment' | 'diagnostics'

const NAV: Array<{ id: Page; label: string }> = [
  { id: 'mission', label: 'Mission' },
  { id: 'assessment', label: 'Assessment' },
  { id: 'diagnostics', label: 'Diagnostics' },
]

function pageFromHash(): Page {
  const hash = window.location.hash
  if (hash === '#assessment' || hash === '#reasoning' || hash === '#heatmap' || hash === '#sensors') return 'assessment'
  if (hash === '#diagnostics' || hash === '#how' || hash === '#about' || hash === '#architecture' || hash === '#legacy') return 'diagnostics'
  return 'mission'
}

export default function App() {
  const [page, setPage] = useState<Page>(pageFromHash)
  const [manualOpen, setManualOpen] = useState(window.location.hash === '#remote')
  const [helpOpen, setHelpOpen] = useState(false)
  const [devOpen, setDevOpen] = useState(window.location.hash === '#legacy')
  const { snapshot, connection } = useOperations()
  const connected = connection === 'connected'

  const openPage = (next: Page) => {
    setHelpOpen(false)
    setPage(next)
    const hash = next === 'mission' ? '' : `#${next}`
    if (window.location.hash !== hash) window.history.replaceState(null, '', hash || window.location.pathname)
  }

  return (
    <div className={page === 'mission' ? 'app-shell is-live' : 'app-shell is-page'} data-testid={page === 'mission' ? 'app-shell' : undefined}>
      <header className="app-header">
        <div className="brand">
          <h1>RubbleEcho</h1>
          <span>Sand table Rev C</span>
        </div>
        <nav className="primary-nav" aria-label="Main navigation">
          {NAV.map((item) => (
            <button key={item.id} type="button" aria-current={page === item.id ? 'page' : undefined} onClick={() => openPage(item.id)}>
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
              <button type="button" onClick={() => { setHelpOpen(false); setDevOpen(true); openPage('diagnostics') }}>About and fixtures</button>
            </div>
          </details>
          <HeaderStart connected={connected} running={Boolean(snapshot?.run_active)} />
          <HeaderStop connected={connected} />
        </div>
      </header>
      {page === 'mission' ? (
        <LiveOperations snapshot={snapshot} connected={connected} onManual={() => setManualOpen(true)} />
      ) : (
        <main className="page-scroll">
          {page === 'assessment' ? (
            <>
              <ReasoningPage snapshot={snapshot} />
              <HeatmapPage snapshot={snapshot} />
              <SensorsPage snapshot={snapshot} />
            </>
          ) : null}
          {page === 'diagnostics' ? (
            <>
              <DiagnosticsPage snapshot={snapshot} />
              <details className="ops-card" open={devOpen} onToggle={(event) => setDevOpen(event.currentTarget.open)}>
                <summary>Developer fixtures</summary>
                <p className="mt-2 text-sm text-slate-600">Replay and scripted rows are fixtures. They are not live evidence and they do not drive the motors.</p>
                <HowItWorks />
                <About />
                <Architecture />
                <LegacyPanel startOpen={devOpen} />
              </details>
            </>
          ) : null}
        </main>
      )}
      {manualOpen ? (
        <div className="manual-drawer" role="dialog" aria-label="Manual control">
          <RemotePage onDashboard={() => setManualOpen(false)} />
        </div>
      ) : null}
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

function HeaderStart({ connected, running }: { connected: boolean; running: boolean }) {
  const [failed, setFailed] = useState(false)
  return (
    <button
      type="button"
      className="start-btn"
      disabled={!connected || running}
      title={running ? 'The nine squares are in progress. STOP ends it.' : 'Send A. The rover drives the nine squares from row 1.'}
      onClick={() => {
        const allowed = window.confirm('This sends A. The rover drives the nine squares from row 1, the first square. Continue?')
        if (!allowed) return
        startHardware().then(() => setFailed(false)).catch(() => setFailed(true))
      }}
    >
      {failed ? 'Arm failed' : running ? 'Armed' : 'Arm rover'}
    </button>
  )
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
