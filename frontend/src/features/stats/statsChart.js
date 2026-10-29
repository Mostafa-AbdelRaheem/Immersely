// src/features/stats/statsChart.js
import { formatDayLabel, formatPercent } from './statsFormat.js'

const round1 = (v) => Math.round(v * 10) / 10

export function barTitle(point) {
  const day = formatDayLabel(point.day)
  const n = point.counts.total
  if (n === 0) return `${day}: no reviews`
  return `${day}: ${formatPercent(point.accuracy)} (${n} ${n === 1 ? 'review' : 'reviews'})`
}

// series: DayPointOut[] from the API. Returns bar rectangles in SVG units.
export function buildBars(series, { width = 600, height = 160 } = {}) {
  const pad = { left: 32, right: 8, top: 16, bottom: 20 }
  const innerW = width - pad.left - pad.right
  const innerH = height - pad.top - pad.bottom
  const n = series.length
  const step = n > 0 ? innerW / n : 0
  const barW = Math.max(1, step * 0.7)

  const bars = series.map((point, i) => {
    const x = pad.left + i * step + (step - barW) / 2
    const empty = point.accuracy === null
    const h = empty ? 0 : Math.max(point.accuracy * innerH, 2)
    return {
      day: point.day,
      empty,
      x: round1(x),
      w: round1(barW),
      y: round1(pad.top + innerH - h),
      h: round1(h),
      cx: round1(x + barW / 2),
      title: barTitle(point),
    }
  })

  return { bars, width, height, pad, innerW, innerH }
}