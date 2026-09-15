// src/features/session/DueTodayBadge.jsx
import { useEffect, useState } from 'react'
import { getDueCount } from '../../api/srs'

export default function DueTodayBadge({ topic }) {
  const [count, setCount] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    setCount(null)
    setError(false)

    getDueCount(topic)
      .then((data) => {
        if (!cancelled) setCount(data.count)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })

    return () => {
      cancelled = true
    }
  }, [topic])

  if (error) return null
  if (count === null) {
    return <span className="due-today-badge due-today-badge--loading">…</span>
  }

  return (
    <span className="due-today-badge" aria-label={`${count} sentences due today`}>
      {count} due today
    </span>
  )
}