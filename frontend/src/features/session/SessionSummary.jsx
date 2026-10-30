// src/features/session/SessionSummary.jsx
function formatDue(iso) {
  return iso ? new Date(iso).toLocaleString() : '—'
}

export default function SessionSummary({ summary, onRestart }) {
  const { total, tiers, overrides, nextDue } = summary

  return (
    <div className="session-summary">
      <h2>Session complete</h2>
      <p className="page-subtitle">
        You reviewed {total} {total === 1 ? 'sentence' : 'sentences'}.
      </p>

      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-card-label">Correct</span>
          <strong>{tiers.correct}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Almost correct</span>
          <strong>{tiers.almost_correct}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Incorrect</span>
          <strong>{tiers.incorrect}</strong>
        </div>
      </div>

      <p className="session-summary-meta">
        Grades you changed: {overrides}
        <br />
        Next review due: {formatDue(nextDue)}
      </p>

      <button type="button" className="btn btn-primary" onClick={onRestart}>
        Back to start
      </button>
    </div>
  )
}