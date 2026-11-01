// src/features/session/FlipCard.jsx
import './FlipCard.css'

const SIDES = {
  'en-de': { front: 'en', back: 'de' },
  'de-en': { front: 'de', back: 'en' },
}

const LABELS = { en: 'English', de: 'German' }

export default function FlipCard({ card, direction, revealed, disabled, onFlip }) {
  const sides = SIDES[direction] ?? SIDES['en-de']

  return (
    <button
      type="button"
      className={`flip-card${revealed ? ' flip-card--revealed' : ''}`}
      onClick={onFlip}
      disabled={disabled}
      aria-label={revealed ? 'Flip card back to the question' : 'Flip card to show the answer'}
    >
      <span className="flip-card-inner">
        <span className="flip-card-face flip-card-face--front" aria-hidden={revealed}>
          <span className="flip-card-label">{LABELS[sides.front]}</span>
          <span className="flip-card-text" lang={sides.front}>
            {card[sides.front]}
          </span>
          <span className="flip-card-hint">Click to flip</span>
        </span>

        <span className="flip-card-face flip-card-face--back" aria-hidden={!revealed}>
          <span className="flip-card-label">{LABELS[sides.back]}</span>
          <span className="flip-card-text" lang={sides.back}>
            {card[sides.back]}
          </span>
          <span className="flip-card-hint">Click to flip back</span>
        </span>
      </span>

      <span className="flip-card-live" aria-live="polite">
        {revealed ? `${LABELS[sides.back]}: ${card[sides.back]}` : ''}
      </span>
    </button>
  )
}