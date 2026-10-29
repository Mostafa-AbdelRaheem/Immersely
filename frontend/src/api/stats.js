// src/api/stats.js
import { apiFetch } from './client'

export const RANGES = ['7d', '30d', '90d', 'all']

export function browserTimeZone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  } catch {
    return 'UTC'
  }
}

export function summaryPath(range, tz) {
  const query = new URLSearchParams({ range, tz }).toString()
  return `/stats/summary?${query}`
}

export function getStatsSummary(range = '30d', tz = browserTimeZone()) {
  return apiFetch(summaryPath(range, tz))
}