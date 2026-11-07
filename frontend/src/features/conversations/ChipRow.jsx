// src/features/conversations/ChipRow.jsx
// "You could say" hints: English first, tap to reveal the German.
// Revealed state is local; the page remounts this row (via key) each turn.
import { useState } from 'react'
import './ChipRow.css'

export default function ChipRow({ chips }) {
  const [revealed, setRevealed] = useState(() => new Set())

  if (!chips || chips.length === 0) return null

  function toggle(id) {
    setRevealed((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="chip-row">
      <span className="chip-row-label">You could say</span>
      <ul className="chip-row-list">
        {chips.map((chip) => {
          const isOpen = revealed.has(chip.id)
          return (
            <li key={chip.id}>
              <button
                type="button"
                className={`chip${isOpen ? ' chip--open' : ''}`}
                aria-expanded={isOpen}
                onClick={() => toggle(chip.id)}
              >
                <span className="chip-en">{chip.en}</span>
                {isOpen && <span className="chip-de">{chip.de}</span>}
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}