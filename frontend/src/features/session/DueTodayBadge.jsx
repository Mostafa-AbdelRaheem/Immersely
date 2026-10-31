// src/features/session/DueTodayBadge.jsx
import { useDueCount } from '../../context/DueCountContext'
import './DueTodayBadge.css'

export default function DueTodayBadge() {
  const { count, error } = useDueCount()

  // Never loaded and the load failed: show nothing rather than a stale or fake number.
  if (count === null && error) return null

  if (count === null) {
    return <span className="due-today-badge due-today-badge--loading">…</span>
  }

  return (
    <span className="due-today-badge" aria-label={`${count} sentences due today`}>
      {count} due today
    </span>
  )
}