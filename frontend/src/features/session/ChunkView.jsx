// src/features/session/ChunkView.jsx
import { useState } from 'react'

export default function ChunkView({
  chunk,
  mode,
  phase,
  hintVisible,
  error,
  onRevealHint,
  onSubmit,
  onFinish,
}) {
  const [text, setText] = useState('')
  const { target, filler_lines: fillerLines } = chunk
  const locked = phase !== 'answering'

  function handleSubmit(e) {
    e.preventDefault()
    if (!locked && text.trim()) onSubmit(text)
  }

  return (
    <div className="session-chunk">
      {fillerLines.length > 0 && (
        <div className="session-filler">
          {fillerLines.map((line, i) => (
            <p key={i} className="session-filler-line">{line}</p>
          ))}
        </div>
      )}

      {target ? (
        <form className="session-target" onSubmit={handleSubmit}>
          <p className="session-prompt">
            {mode === 'isolated' ? 'Translate into German:' : 'Say it in German:'}
          </p>

          {hintVisible && <p className="session-hint">{target.hint_en}</p>}
          {!hintVisible && phase === 'answering' && (
            <button type="button" className="btn btn-secondary" onClick={onRevealHint}>
              Show hint
            </button>
          )}

          <div className="session-answer-row">
            {target.speaker && (
              <span className="session-speaker">{target.speaker}:</span>
            )}
            <input
              type="text"
              className="session-input"
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={locked}
              maxLength={500}
              autoFocus
              aria-label="Your German sentence"
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={locked || !text.trim()}
            >
              {phase === 'checking' ? 'Checking…' : 'Check'}
            </button>
          </div>

          {error && <p className="form-error">{error}</p>}
        </form>
      ) : (
        <button type="button" className="btn btn-primary" onClick={onFinish}>
          Finish
        </button>
      )}
    </div>
  )
}