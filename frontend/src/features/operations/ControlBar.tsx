import { useState } from 'react'
import {
  clearOperationsView,
  downloadExport,
  loadReplay,
  readOperatorToken,
  requestAdvisory,
  sendEstop,
  writeOperatorToken,
} from '../../api/operations'
import type { OperationsSnapshot } from '../../types/operations'

export default function ControlBar({
  snapshot,
  connected,
}: {
  snapshot: OperationsSnapshot | null
  connected: boolean
}) {
  const [token, setToken] = useState(readOperatorToken)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const remember = (value: string) => {
    setToken(value)
    writeOperatorToken(value)
  }

  const run = async (action: () => Promise<void>) => {
    setError('')
    setMessage('')
    try {
      await action()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Request failed')
    }
  }

  return (
    <section className="ops-card">
      <h2 className="text-xl font-semibold">Operator controls</h2>
      <label className="mt-3 block text-sm" htmlFor="operator-token">
        Local operator token
        <input
          id="operator-token"
          type="password"
          autoComplete="off"
          value={token}
          onChange={(event) => remember(event.target.value)}
          className="mt-1 w-full rounded-lg border border-[#E1E7EF] px-3 py-2"
        />
      </label>
      <p className="mt-1 text-xs text-slate-500">The token stays in this browser tab. It is not sent to Nebius.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" className="rounded-lg bg-[#2463EB] px-3 py-2 text-sm text-white disabled:bg-slate-300" disabled={!token} onClick={() => run(async () => { await loadReplay(); setMessage('Replay fixture loaded. It is not live hardware.') })}>Load replay</button>
        <button type="button" className="rounded-lg bg-[#2463EB] px-3 py-2 text-sm text-white disabled:bg-slate-300" disabled={!token} onClick={() => run(async () => { await requestAdvisory(); setMessage('Advisory requested.') })}>Request advisory</button>
        <button type="button" className="rounded-lg bg-[#B91C1C] px-3 py-2 text-sm font-semibold text-white disabled:bg-slate-300" disabled={!connected} title={connected ? 'Local software stop' : 'Safety controller unreachable'} onClick={() => run(async () => { await sendEstop(); setMessage('STOP sent. This does not replace a hardware e-stop.') })}>STOP</button>
        <button type="button" className="rounded-lg border border-[#E1E7EF] px-3 py-2 text-sm disabled:bg-slate-100" disabled={!token || !snapshot?.trial_id} onClick={() => run(async () => { if (!snapshot?.trial_id) return; await downloadExport(snapshot.trial_id, 'zip'); setMessage('Export downloaded.') })}>Export ZIP</button>
        <button
          type="button"
          className="rounded-lg border border-[#E1E7EF] px-3 py-2 text-sm"
          disabled={!token}
          onClick={() => run(async () => {
            if (!window.confirm('Clear the on-screen trial? Exported files already downloaded are not deleted.')) return
            await clearOperationsView()
            setMessage('View cleared. Stored exports were not deleted.')
          })}
        >
          Reset view
        </button>
      </div>
      {error ? <p role="alert" className="mt-3 text-sm text-red-700">{error}</p> : null}
      {message ? <p role="status" className="mt-3 text-sm text-teal-800">{message}</p> : null}
    </section>
  )
}
