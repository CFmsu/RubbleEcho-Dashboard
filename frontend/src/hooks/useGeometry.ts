import { useEffect, useState } from 'react'
import { fetchGeometry } from '../api/operations'
import type { TableGeometry } from '../types/operations'

function isGeometry(value: unknown): value is TableGeometry {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return typeof record.outer_cm === 'object' && Array.isArray(record.boxes) && Array.isArray(record.measurement_points)
}

export function useGeometry() {
  const [geometry, setGeometry] = useState<TableGeometry | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    fetchGeometry()
      .then((payload) => {
        if (!active) return
        if (!isGeometry(payload)) {
          setError('Geometry response was not usable.')
          return
        }
        setGeometry(payload)
      })
      .catch(() => {
        if (active) setError('Table geometry is unavailable.')
      })
    return () => {
      active = false
    }
  }, [])

  return { geometry, error }
}
