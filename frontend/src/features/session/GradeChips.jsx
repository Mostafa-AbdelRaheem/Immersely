// src/features/session/GradeChips.jsx
const GRADES = [
  { value: 'again', label: 'Again' },
  { value: 'hard', label: 'Hard' },
  { value: 'good', label: 'Good' },
  { value: 'easy', label: 'Easy' },
]

export default function GradeChips({ selected, suggested, disabled, onSelect }) {
  return (
    <div className="grade-chips" role="group" aria-label="Grade">
      {GRADES.map(({ value, label }) => {
        const isSelected = selected === value
        return (
          <div key={value} className="grade-chip-wrap">
            <button
              type="button"
              className={`grade-chip grade-chip--${value}${isSelected ? ' grade-chip--selected' : ''}`}
              aria-pressed={isSelected}
              disabled={disabled}
              onClick={() => onSelect(value)}
            >
              {isSelected ? '✓ ' : ''}{label}
            </button>
            <span className="grade-chip-suggested">
              {suggested === value ? 'Suggested' : '\u00A0'}
            </span>
          </div>
        )
      })}
    </div>
  )
}