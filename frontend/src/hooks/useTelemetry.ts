
import { useEffect, useState } from 'react'
import type { Telemetry } from '../types/telemetry'
import { isValidTelemetry } from '../types/telemetryValidation'

const emptyTelemetry: Telemetry = {
  mission: { status: 'STANDBY', phase: 'explore', scenario: 'collapse', probe_count: 0, confidence: 0 },
  robot: { x: 0, y: 0 },
  probes: [],
  events: [],
}

type ConnectionStatus =
  | 'connecting'
  | 'connected'
  | 'disconnected'

export function useTelemetry() {
  const [telemetry, setTelemetry] = useState<Telemetry>(
    emptyTelemetry
  )

  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('connecting')

  useEffect(() => {
    const wsProtocol =
    window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  
  const wsUrl =
    import.meta.env.VITE_WS_URL ||
    `${wsProtocol}//${window.location.host}/ws/telemetry`

    let socket: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let isUnmounted = false

    const connect = () => {
      if (isUnmounted) return

      setConnectionStatus('connecting')

      try {
        socket = new WebSocket(wsUrl)
      } catch {
        setConnectionStatus('disconnected')
        scheduleReconnect()
        return
      }

      socket.onopen = () => {
        if (isUnmounted) return
        setConnectionStatus('connected')
      }

      socket.onmessage = (event) => {
        try {
          const data: unknown = JSON.parse(event.data)

          if (isValidTelemetry(data)) {
            setTelemetry(data)
          } else {
            console.warn('Invalid telemetry structure received')
          }
        } catch {
          console.error('Failed to parse WebSocket telemetry')
        }
      }

      socket.onerror = () => {
        if (isUnmounted) return
        setConnectionStatus('disconnected')
      }

      socket.onclose = () => {
        if (isUnmounted) return

        setConnectionStatus('disconnected')
        scheduleReconnect()
      }
    }

    const scheduleReconnect = () => {
      if (isUnmounted || reconnectTimer !== null) return

      reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        connect()
      }, 3000)
    }

    connect()

    return () => {
      isUnmounted = true

      if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer)
      }

      if (socket) {
        socket.close()
      }
    }
  }, [])

  return { telemetry, connectionStatus }
}
