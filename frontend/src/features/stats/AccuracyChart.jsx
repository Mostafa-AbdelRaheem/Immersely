// src/features/stats/AccuracyChart.jsx
import { buildBars } from './statsChart'
import { formatDayLabel } from './statsFormat'
import './stats.css'
import './AccuracyChart.css'

const GRID = [0, 0.5, 1]

export default function AccuracyChart({ series }) {
  const { bars, width, height, pad, innerW, innerH } = buildBars(series)
  const baseY = pad.top + innerH
  const labelIdx = [...new Set([0, Math.floor((series.length - 1) / 2), series.length - 1])]
  const reviewed = series.filter((p) => p.accuracy !== null).length

  return (
    <figure className="stats-chart">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="stats-chart-svg"
        role="img"
        aria-label={`Daily accuracy over ${series.length} days, ${reviewed} days with reviews`}
      >
        {GRID.map((g) => {
          const y = baseY - g * innerH
          return (
            <g key={g}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} className="stats-chart-grid" />
              <text x={pad.left - 6} y={y + 3} textAnchor="end" className="stats-chart-label">
                {Math.round(g * 100)}%
              </text>
            </g>
          )
        })}

        {bars.map((b) =>
          b.empty ? (
            <line key={b.day} x1={b.cx - 2} x2={b.cx + 2} y1={baseY + 3} y2={baseY + 3} className="stats-chart-empty">
              <title>{b.title}</title>
            </line>
          ) : (
            <rect key={b.day} x={b.x} y={b.y} width={b.w} height={b.h} rx="1" className="stats-chart-bar">
              <title>{b.title}</title>
            </rect>
          ),
        )}

        {labelIdx.map((i) => (
          <text key={i} x={bars[i].cx} y={height - 4} textAnchor="middle" className="stats-chart-label">
            {formatDayLabel(series[i].day)}
          </text>
        ))}
      </svg>
      <figcaption className="stats-note">
        Daily accuracy. A small tick below the line means no reviews that day.
      </figcaption>
    </figure>
  )
}