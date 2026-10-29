// src/features/stats/StatsPage.jsx
import { useState } from 'react'
import { RANGES } from '../../api/stats'
import { useStatsSummary } from './useStatsSummary'
import { formatPercent, formatTierBreakdown } from './statsFormat'
import AccuracyChart from './AccuracyChart'
import TopicList from './TopicList'


const RANGE_LABELS = { '7d': '7 days', '30d': '30 days', '90d': '90 days', all: 'All time' }

export default function StatsPage() {
  const [range, setRange] = useState('30d')
  const { data, loading, error } = useStatsSummary(range)

  return (
    <div className="stats-page">
      <div className="stats-header">
        <h1>Stats</h1>
        <div className="stats-range" role="group" aria-label="Time range">
          {RANGES.map((r) => (
            <button
              key={r}
              type="button"
              className={`stats-range-btn${r === range ? ' stats-range-btn--active' : ''}`}
              aria-pressed={r === range}
              onClick={() => setRange(r)}
            >
              {RANGE_LABELS[r]}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p className="form-error" role="alert">
          Could not load your stats right now. Please try again.
        </p>
      )}

      {!data && loading && <p className="empty-state">Loading…</p>}

      {data && (
        <div className={`stats-body${loading ? ' stats-body--loading' : ''}`}>
          <div className="home-cards">
            <div className="home-card">
              <span className="home-card-label">Accuracy</span>
              <strong className="stats-big">{formatPercent(data.accuracy)}</strong>
              {data.totals.total === 0 ? (
                <span className="stats-note">No reviews in this period</span>
              ) : (
                <>
                  <span className="stats-note">Based on {data.totals.total} reviews</span>
                  <span className="stats-note">{formatTierBreakdown(data.totals)}</span>
                </>
              )}
            </div>

            <div className="home-card">
              <span className="home-card-label">Current streak</span>
              <strong className="stats-big">{data.streaks.current}</strong>
              <span className="stats-note">days in a row</span>
            </div>

            <div className="home-card">
              <span className="home-card-label">Longest streak</span>
              <strong className="stats-big">{data.streaks.longest}</strong>
              <span className="stats-note">days in a row</span>
            </div>
          </div>
          <div className="home-card">
            <span className="home-card-label">Daily accuracy</span>
            <AccuracyChart series={data.series} />
          </div>
          {data.topics.length > 0 && (
            <div className="home-card">
              <span className="home-card-label">By topic</span>
              <TopicList topics={data.topics} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}