
import { useEffect, useState } from 'react'
import type { Scenario, MissionStatus } from '../types/telemetry'
import { sendMissionCommand } from '../api/mission'
import type { MissionAction } from '../api/mission'

// Temporary scenarios while backend is offline
const fallbackScenarios: Scenario[] = [
  'earthquake',
  'flood',
  'collapse',
]

interface MissionControlsProps {
  missionStatus: MissionStatus
  telemetryConnected: boolean
}

function MissionControls({
  missionStatus,
  telemetryConnected,
}: MissionControlsProps) {
  const [scenario, setScenario] = useState<Scenario>('collapse')
  const [scenarios, setScenarios] =
    useState<Scenario[]>(fallbackScenarios)
  const [usingFallback, setUsingFallback] = useState(true)

  const [backendOnline, setBackendOnline] = useState(false)
  const [sending, setSending] = useState(false)
  const [commandError, setCommandError] = useState('')
  const [commandMessage, setCommandMessage] = useState('')


  const handleCommand = async (action: MissionAction) => {
    if (!backendOnline || sending) return

    setSending(true)
    setCommandError('')
    setCommandMessage('')

    try {
      await sendMissionCommand(action, scenario)
      setCommandMessage(`${action} command sent successfully.`)
    } catch {
      setCommandError(`Failed to send ${action} command.`)
    } finally {
      setSending(false)
    }
  }

  
useEffect(() => {
  let active = true

  const checkBackend = async () => {
    try {
      const response = await fetch('/api/health', {
        cache: 'no-store',
        signal: AbortSignal.timeout(3000),
      })

      if (active) {
        setBackendOnline(response.ok)
      }
    } catch {
      if (active) {
        setBackendOnline(false)
      }
    }
  }

  checkBackend()
  const interval = setInterval(checkBackend, 5000)

  return () => {
    active = false
    clearInterval(interval)
  }
}, [])

  useEffect(() => {
    const controller = new AbortController()

    const loadScenarios = async () => {
      try {
        const response = await fetch('/api/scenarios', {
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error('Failed to load scenarios')
        }

        const data: unknown = await response.json()

        // Validate the response before using it
        
        const validIds: Scenario[] = [
          'earthquake',
          'flood',
          'collapse',
        ]

        if (!Array.isArray(data) || data.length === 0) {
          throw new Error('Invalid scenario response')
        }

        const available: Scenario[] = data.map((item: unknown) => {
          if (typeof item !== 'object' || item === null) {
            throw new Error('Invalid scenario object')
          }

          const scenario = item as Record<string, unknown>

          if (
            typeof scenario.id !== 'string' ||
            !validIds.includes(scenario.id as Scenario) ||
            typeof scenario.label !== 'string' ||
            typeof scenario.width !== 'number' ||
            typeof scenario.height !== 'number'
          ) {
            throw new Error('Invalid scenario fields')
          }

          return scenario.id as Scenario
        })

        setScenarios(available)
        setUsingFallback(false)

        setScenario((current) =>
          available.includes(current) ? current : available[0]
        )
      } catch {
        if (controller.signal.aborted) return

        setScenarios(fallbackScenarios)
        setUsingFallback(true)
      }
    }

    loadScenarios()

    return () => controller.abort()
  }, [])

  
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!backendOnline || sending) return

      const target = event.target

      // Ignore shortcuts while typing or selecting a scenario
      if (
        target instanceof HTMLElement &&
        (target.isContentEditable ||
          ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(target.tagName))
      ) {
        return
      }

      if (event.ctrlKey || event.metaKey || event.altKey || event.repeat) {
        return
      }
      
      switch (event.key.toLowerCase()) {
        case ' ':
          if (!telemetryConnected) return

          if (missionStatus === 'ACTIVE') {
            event.preventDefault()
            void handleCommand('pause')
          } else if (missionStatus === 'PAUSED') {
            event.preventDefault()
            void handleCommand('resume')
          }
          break

        case 'n':
          void handleCommand('step')
          break

        case 'r':
          void handleCommand('reset')
          break

        case 'd':
          void handleCommand('demo')
          break
      }

    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  })

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-xl font-semibold">
        Mission Controls
      </h3>

      <div className="mb-5">
        <label
          htmlFor="scenario"
          className="mb-2 block font-medium text-slate-700"
        >
          Select Scenario
        </label>

        <select
          id="scenario"
          value={scenario}
          onChange={(e) =>
            setScenario(e.target.value as Scenario)
          }
          className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3"
        >
          {scenarios.map((item) => (
            <option key={item} value={item}>
              {item.charAt(0).toUpperCase() + item.slice(1)}
            </option>
          ))}
        </select>

        {usingFallback && (
          <p className="mt-2 text-sm text-amber-700">
            Using local scenarios. Backend unavailable.
          </p>
        )}
      </div>
      
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
        {['Demo', 'Start', 'Pause', 'Resume', 'Step', 'Reset'].map(
          (action) => (
            <button
              key={action}
              type="button"
              aria-label={`${action} mission`}
              onClick={() => handleCommand(action.toLowerCase() as MissionAction)}
              disabled={!backendOnline || sending}
              className="w-full rounded-lg bg-blue-600 px-2 py-3
                        text-center text-sm font-medium text-white
                        hover:bg-blue-700
                        disabled:cursor-not-allowed
                        disabled:bg-slate-400"
            >
              {action}
            </button>
          )
        )}
      </div>

      {!backendOnline && (
        <p className="mt-4 text-sm text-amber-700">
          Mission controls unavailable. Backend is offline.
        </p>
      )}

      {commandError && (
        <p role="alert" className="mt-4 text-sm text-red-600">
          {commandError}
        </p>
      )}

      {commandMessage && (
        <p role="status" className="mt-4 text-sm text-green-700">
          {commandMessage}
        </p>
      )}

    </div>
  )
}

export default MissionControls
