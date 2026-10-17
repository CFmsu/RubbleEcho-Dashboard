
import { useEffect, useState } from 'react'
import type { Telemetry } from '../types/telemetry'
import sampleTelemetry from '../data/sampleTelemetry.json'

type ConnectionStatus =
  | 'connecting'
  | 'connected'
  | 'disconnected'

export function useTelemetry() {
  const [telemetry, setTelemetry] = useState<Telemetry>(
    sampleTelemetry as Telemetry
  )

  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('connecting')

  useEffect(() => {
    // Temporary URL until backend details are confirmed
    const wsUrl =
      import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

    let socket: WebSocket

    try {
      socket = new WebSocket(wsUrl)
    } catch {
      setConnectionStatus('disconnected')
      return
    }

    socket.onopen = () => {
      setConnectionStatus('connected')
    }

    socket.onmessage = (event) => {
      try {
        const data: unknown = JSON.parse(event.data)

        // Basic validation before updating the dashboard
        if (
          typeof data === 'object' &&
          data !== null &&
          'mission' in data &&
          'robot' in data &&
          'probes' in data &&
          'events' in data
        ) {
          setTelemetry(data as Telemetry)
        }
      } catch {
        console.error('Invalid WebSocket telemetry')
      }
    }

    socket.onerror = () => {
      setConnectionStatus('disconnected')
    }

    socket.onclose = () => {
      setConnectionStatus('disconnected')
    }

    return () => {
      socket.close()
    }
  }, [])

  return { telemetry, connectionStatus }
}
