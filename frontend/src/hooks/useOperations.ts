import { useEffect, useState } from 'react'
import { isOperationsSnapshot, type OperationsSnapshot } from '../types/operations'

export function useOperations() {
  const [snapshot, setSnapshot] = useState<OperationsSnapshot | null>(null)
  const [connection, setConnection] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')

  useEffect(() => {
    let socket: WebSocket | null = null
    let timer: ReturnType<typeof setTimeout> | null = null
    let stopped = false
    let delay = 500

    const connect = () => {
      if (stopped) return
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      setConnection('connecting')
      socket = new WebSocket(`${protocol}//${window.location.host}/ws/operations`)
      socket.onopen = () => {
        delay = 500
        setConnection('connected')
      }
      socket.onmessage = (event) => {
        try {
          const data: unknown = JSON.parse(String(event.data))
          if (isOperationsSnapshot(data)) setSnapshot(data)
        } catch {
          setConnection('disconnected')
        }
      }
      socket.onclose = () => {
        if (stopped) return
        setConnection('disconnected')
        timer = setTimeout(connect, delay)
        delay = Math.min(delay * 2, 8000)
      }
    }

    connect()
    return () => {
      stopped = true
      if (timer !== null) clearTimeout(timer)
      socket?.close()
    }
  }, [])

  return { snapshot, connection }
}
