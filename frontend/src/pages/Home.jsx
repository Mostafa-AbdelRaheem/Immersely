import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client.js'
import { useAuth } from '../context/AuthContext'
import DueTodayBadge from '../features/session/DueTodayBadge'
// import CorrectionFeedback from '../features/session/CorrectionFeedback' // TEMP - M6 validation

function Home() {
  const [status, setStatus] = useState('checking...')
  const { user } = useAuth()

  useEffect(() => {
    apiFetch('/health')
      .then((data) => setStatus(data.status))
      .catch(() => setStatus('unreachable'))
  }, [])

  return (
    <div className="home-page">
      <div className="home-hero">
        <h1>Welcome back{user?.email ? `, ${user.email}` : ''}</h1>
        <p className="home-subtitle">Here's where things stand today.</p>
      </div>

      <div className="home-cards">
        <div className="home-card">
          <span className="home-card-label">Backend status</span>
          <span className={`status-pill status-pill--${status === 'ok' ? 'ok' : 'down'}`}>
            {status}
          </span>
        </div>

        <div className="home-card">
          <span className="home-card-label">Review queue</span>
          <DueTodayBadge />
        </div>
      </div>

      {/* TEMP - M6 CorrectionFeedback validation, remove after confirming */}
      {/* <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '2rem' }}>
        <CorrectionFeedback result={{
          tier: 'correct',
          suggested_grade: 'good',
          model_answer: 'Ich gehe heute ins Kino.',
          corrected_input: null,
          diff_note: null,
          rule_practiced: null,
          rule_note: null,
        }} />

        <CorrectionFeedback result={{
          tier: 'correct',
          suggested_grade: 'good',
          model_answer: 'Ich haette gern einen Kaffee.',
          corrected_input: null,
          diff_note: null,
          rule_practiced: false,
          rule_note: 'The target sentence uses the subjunctive II "hätte" to express a polite wish, while your sentence uses the indicative "nehme" to state an intention.',
        }} />

        <CorrectionFeedback result={{
          tier: 'almost_correct',
          suggested_grade: 'hard',
          model_answer: 'Ich gehe heute ins Kino.',
          corrected_input: 'Ich gehe heute ins Kino.',
          diff_note: "Changed 'im' to 'ins'.",
          rule_practiced: null,
          rule_note: null,
        }} />

        <CorrectionFeedback result={{
          tier: 'incorrect',
          suggested_grade: 'again',
          model_answer: 'Ich gehe heute ins Kino.',
          corrected_input: null,
          diff_note: null,
          rule_practiced: null,
          rule_note: null,
        }} />
      </div> */}
      {/* END TEMP */}
    </div>
  )
}

export default Home