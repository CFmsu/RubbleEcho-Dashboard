
import { useEffect, useState } from 'react'
import type { Telemetry } from '../types/telemetry'
import sampleTelemetry from '../data/sampleTelemetry.json'
import { isValidTelemetry } from '../types/telemetryValidation'

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
        import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws/telemetry'

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
