// src/features/session/FlipSummary.jsx
import './SessionSummary.css'

function formatDue(iso) {
  return iso ? new Date(iso).toLocaleString() : '—'
}

export default function FlipSummary({ summary, onRestart }) {
  const { reviews, cards, grades, nextDue } = summary

  return (
    <div className="session-summary">
      <h2>Session complete</h2>
      <p className="page-subtitle">
        You reviewed {cards} {cards === 1 ? 'card' : 'cards'}
        {reviews !== cards && ` (${reviews} reviews, including repeats)`}.
      </p>

      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-card-label">Again</span>
          <strong>{grades.again}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Hard</span>
          <strong>{grades.hard}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Good</span>
          <strong>{grades.good}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Easy</span>
          <strong>{grades.easy}</strong>
        </div>
      </div>

      <p className="session-summary-meta">
        Next review due: {formatDue(nextDue)}
      </p>

      <button type="button" className="btn btn-primary" onClick={onRestart}>
        Back to start
      </button>
    </div>
  )
}