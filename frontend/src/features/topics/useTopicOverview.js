// src/features/topics/useTopicOverview.js
import { useCallback, useEffect, useState } from 'react'
import { getTopicOverview } from '../../api/topics'

export function useTopicOverview() {
  const [overview, setOverview] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      setError(null)
      try {
        const data = await getTopicOverview()
        if (!cancelled) setOverview(data)
      } catch {
        if (!cancelled) setError('Could not load your topics. Please try again.')
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  const reload = useCallback(() => setReloadKey((k) => k + 1), [])

  return { overview, isLoading, error, reload }
}