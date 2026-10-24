import { useState } from 'react'
import About from './components/About'
import HowItWorks from './components/HowItWorks'
import DiagnosticsPage from './features/diagnostics/DiagnosticsPage'
import HeatmapPage from './features/heatmap/HeatmapPage'
import OperationsPage from './features/operations/OperationsPage'
import ReasoningPage from './features/reasoning/ReasoningPage'
import SensorsPage from './features/sensors/SensorsPage'
import { useOperations } from './hooks/useOperations'
import { Architecture } from './pages/Architecture'

type Page = 'live' | 'sensors' | 'heatmap' | 'reasoning' | 'diagnostics' | 'how' | 'about' | 'architecture'

const NAV: Array<{ id: Page; label: string }> = [
  { id: 'live', label: 'Live Operations' },
  { id: 'sensors', label: 'Sensors' },
  { id: 'heatmap', label: 'Heatmap & Trials' },
  { id: 'reasoning', label: 'AI Reasoning' },
  { id: 'diagnostics', label: 'Architecture & Diagnostics' },
  { id: 'about', label: 'About' },
  { id: 'how', label: 'How It Works' },
]

export default function App() {
  const [page, setPage] = useState<Page>('live')
  const { snapshot, connection } = useOperations()
  const badge = snapshot?.badge ?? 'DISCONNECTED'

  return (
    <div className="min-h-screen bg-[#F4F7FB] text-[#0E1B32]">
      <header className="bg-[#0E1B32] text-white">
        <div className="mx-auto flex min-h-16 max-w-[1900px] flex-wrap items-center justify-between gap-3 px-5 py-3">
          <div>
            <h1 className="text-xl font-semibold">RubbleEcho</h1>
            <p className="text-xs text-slate-300">Physical AI · Sand Table Rev C</p>
          </div>
          <nav aria-label="Main navigation" className="flex flex-wrap gap-2">
            {NAV.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setPage(item.id)}
                className={`rounded-lg px-3 py-2 text-sm ${page === item.id ? 'bg-[#2463EB] text-white' : 'hover:bg-slate-700'}`}
              >
                {item.label}
              </button>
            ))}
          </nav>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-white/10 px-3 py-1">{badge}</span>
            <span className={snapshot?.system_live ? 'text-emerald-300' : 'text-amber-200'}>
              {snapshot?.system_live ? 'System live' : 'Health policy not met'}
            </span>
            <span>API {connection}</span>
            <span>Safety {snapshot?.safety_state ?? '—'}</span>
            <time dateTime={snapshot?.updated_at_utc}>{snapshot?.updated_at_utc ?? 'no snapshot'}</time>
          </div>
        </div>
      </header>
      <main className="ops-shell">
        {page === 'live' ? <OperationsPage snapshot={snapshot} connected={connection === 'connected'} /> : null}
        {page === 'sensors' ? <SensorsPage snapshot={snapshot} /> : null}
        {page === 'heatmap' ? <HeatmapPage snapshot={snapshot} /> : null}
        {page === 'reasoning' ? <ReasoningPage snapshot={snapshot} /> : null}
        {page === 'diagnostics' ? <DiagnosticsPage snapshot={snapshot} /> : null}
        {page === 'how' ? <HowItWorks /> : null}
        {page === 'about' ? <About /> : null}
        {page === 'architecture' ? <Architecture /> : null}
      </main>
    </div>
  )
}
