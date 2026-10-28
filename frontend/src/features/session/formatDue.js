// src/features/session/formatDue.js
export function formatDueIn(iso, now = Date.now()) {
  const minutes = Math.round((new Date(iso).getTime() - now) / 60000)
  if (minutes < 1) return 'in under a minute'
  if (minutes < 60) return `in ${minutes} min`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `in ${hours} h`
  const days = Math.round(hours / 24)
  return `in ${days} ${days === 1 ? 'day' : 'days'}`
}