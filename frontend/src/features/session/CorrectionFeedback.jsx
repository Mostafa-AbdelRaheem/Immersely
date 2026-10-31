// src/features/session/CorrectionFeedback.jsx
import './CorrectionFeedback.css'

export default function CorrectionFeedback({ result }) {
  const { tier, model_answer, corrected_input, diff_note, rule_practiced, rule_note } = result

  return (
    <div className={`correction-feedback correction-feedback--${tier.replace('_', '-')}`}>
      {tier === 'correct' && (
        <div className="correction-feedback-main">
          <span className="correction-feedback-badge">✓ Correct</span>
        </div>
      )}

      {tier === 'almost_correct' && (
        <div className="correction-feedback-main">
          <span className="correction-feedback-badge">Almost there</span>
          <p className="correction-feedback-text">{corrected_input}</p>
          {diff_note && <p className="correction-feedback-note">{diff_note}</p>}
        </div>
      )}

      {tier === 'incorrect' && (
        <div className="correction-feedback-main">
          <span className="correction-feedback-badge">Not quite</span>
          <p className="correction-feedback-label">Model answer:</p>
          <p className="correction-feedback-text">{model_answer}</p>
        </div>
      )}

      {rule_practiced === false && rule_note && (
        <p className="correction-feedback-rule-note">{rule_note}</p>
      )}
    </div>
  )
}