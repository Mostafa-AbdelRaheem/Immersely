// src/features/stats/statsFormat.js
import { formatTopic } from '../session/formatTopic.js'


export function formatPercent(accuracy) {
  if (accuracy === null || accuracy === undefined) return '–'
  return `${Math.round(accuracy * 100)}%`
}

// isoDay is "YYYY-MM-DD" as sent by the API. Built from parts so the
// browser's timezone can never shift the displayed day.
export function formatDayLabel(isoDay, locale = 'en-GB') {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDay)
  if (!match) return isoDay
  const [, y, m, d] = match
  const date = new Date(Number(y), Number(m) - 1, Number(d))
  return new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short' }).format(date)
}

// The API sends topic: null for sentences without topic tags.
export function topicLabel(topic) {
  return topic === null || topic === undefined ? 'Untagged' : formatTopic(topic)
}

// counts is { correct, almost_correct, incorrect, total } as sent by the API.
export function formatTierBreakdown(counts) {
  return `${counts.correct} correct · ${counts.almost_correct} almost correct · ${counts.incorrect} incorrect`
}