// src/features/session/FlipCard.jsx
import './FlipCard.css'

const SIDES = {
  'en-de': { front: 'en', back: 'de' },
  'de-en': { front: 'de', back: 'en' },
}

const LABELS = { en: 'English', de: 'German' }

export default function FlipCard({ card, direction, revealed, onReveal }) {
  const sides = SIDES[direction] ?? SIDES['en-de']

  return (
    <div className="flip-card">
      <div className="flip-card-side">
        <span className="flip-card-label">{LABELS[sides.front]}</span>
        <p className="flip-card-text" lang={sides.front}>
          {card[sides.front]}
        </p>
      </div>

      {revealed ? (
        <div className="flip-card-side flip-card-side--back">
          <span className="flip-card-label">{LABELS[sides.back]}</span>
          <p className="flip-card-text" lang={sides.back}>
            {card[sides.back]}
          </p>
        </div>
      ) : (
        <button type="button" className="btn btn-primary" onClick={onReveal}>
          Show answer
        </button>
      )}
    </div>
  )
}