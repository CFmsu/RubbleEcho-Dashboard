
import { useEffect, useState } from 'react'

type ConnectionStatus = 'checking' | 'online' | 'offline'

function BackendStatus() {
  const [status, setStatus] =
    useState<ConnectionStatus>('checking')

  useEffect(() => {
    let active = true

    const checkBackend = async () => {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 3000)

      try {
        const response = await fetch('/api/health', {
          signal: controller.signal,
          cache: 'no-store',
        })

        if (active) {
          setStatus(response.ok ? 'online' : 'offline')
        }
      } catch {
        if (active) {
          setStatus('offline')
        }
      } finally {
        clearTimeout(timeout)
      }
    }

    checkBackend()

    const interval = setInterval(checkBackend, 5000)

    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  const colors = {
    checking: 'bg-yellow-100 text-yellow-800',
    online: 'bg-green-100 text-green-800',
    offline: 'bg-red-100 text-red-800',
  }

  const labels = {
    checking: 'Checking backend...',
    online: 'Backend Online',
    offline: 'Backend Offline',
  }

  return (
    <div
      role="status"
      className={`inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium ${colors[status]}`}
    >
      <span
        className={`mr-2 h-2.5 w-2.5 rounded-full ${
          status === 'online'
            ? 'bg-green-600'
            : status === 'offline'
              ? 'bg-red-600'
              : 'bg-yellow-600'
        }`}
      />

      {labels[status]}
    </div>
  )
}

export default BackendStatus
