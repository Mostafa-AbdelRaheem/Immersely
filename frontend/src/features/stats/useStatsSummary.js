// src/features/stats/useStatsSummary.js
import { useEffect, useState } from 'react'
import { getStatsSummary } from '../../api/stats'

export function useStatsSummary(range) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    getStatsSummary(range)
      .then((summary) => {
        if (!cancelled) setData(summary)
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [range])

  return { data, loading, error }
}