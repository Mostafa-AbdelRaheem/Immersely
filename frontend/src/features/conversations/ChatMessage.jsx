// src/features/conversations/ChatMessage.jsx
// One chat bubble. Presentational only: props in, markup out.
// A correction appears under the learner's own message, never under the partner's.
import './ChatMessage.css'

export default function ChatMessage({ message }) {
  const { role, text, correction } = message
  const hasFix =
    role === 'user' && correction && (correction.corrected_text || correction.note)

  return (
    <div className={`chat-message chat-message--${role}`}>
      <p className="chat-bubble">{text}</p>
      {hasFix && (
        <div className="chat-correction">
          <span className="chat-correction-label">
            {correction.corrected_text ? 'Better' : 'Hint'}
          </span>
          {correction.corrected_text && (
            <p className="chat-correction-text">{correction.corrected_text}</p>
          )}
          {correction.note && <p className="chat-correction-note">{correction.note}</p>}
        </div>
      )}
    </div>
  )
}