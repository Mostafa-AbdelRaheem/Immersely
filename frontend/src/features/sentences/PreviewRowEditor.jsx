// src/features/sentences/PreviewRowEditor.jsx
// One editable row in the bulk import review. Fully controlled: the parent
// owns the rows and re-runs recheckRows after every change.
import './sentences.css'

const ISSUE_LABELS = {
  empty_de: 'German sentence is empty.',
  empty_en: 'English sentence is empty.',
  too_long_de: 'German sentence is too long.',
  too_long_en: 'English sentence is too long.',
  duplicate_in_file: 'Same German sentence appears earlier in this file.',
  duplicate_existing: 'You already have this sentence saved.',
}

export default function PreviewRowEditor({ row, allTopics, onChange, onRemove }) {
  const n = row.row_number
  const availableToAdd = allTopics.filter((t) => !row.topics.includes(t))

  function handleAddTopic(e) {
    const topic = e.target.value
    if (!topic) return
    onChange(n, { topics: [...row.topics, topic] })
    e.target.value = ''
  }

  return (
    <div className={`import-row${row.has_blocking_issue ? ' import-row--blocked' : ''}`}>
      <div className="import-row-head">
        <span className="import-row-number">Row {n}</span>
        <button
          type="button"
          className="import-row-remove"
          aria-label={`Remove row ${n}`}
          onClick={() => onRemove(n)}
        >
          ×
        </button>
      </div>

      <div className="import-row-fields">
        <input
          type="text"
          value={row.de}
          aria-label={`Row ${n} German`}
          onChange={(e) => onChange(n, { de: e.target.value })}
        />
        <input
          type="text"
          value={row.en}
          aria-label={`Row ${n} English`}
          onChange={(e) => onChange(n, { en: e.target.value })}
        />
      </div>

      <div className="tag-editor">
        {row.topics.map((t) => (
          <span className="tag-chip" key={t}>
            {t}
            <button
              type="button"
              aria-label={`Remove ${t} from row ${n}`}
              onClick={() => onChange(n, { topics: row.topics.filter((x) => x !== t) })}
            >
              ×
            </button>
          </span>
        ))}

        {availableToAdd.length > 0 && (
          <select
            className="tag-add-select"
            defaultValue=""
            aria-label={`Add topic to row ${n}`}
            onChange={handleAddTopic}
          >
            <option value="" disabled>
              + add topic
            </option>
            {availableToAdd.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        )}

        <input
          className="grammar-tag-input"
          type="text"
          value={row.grammar_tag ?? ''}
          aria-label={`Row ${n} grammar tag`}
          onChange={(e) => onChange(n, { grammar_tag: e.target.value })}
          placeholder="grammar tag"
        />
      </div>

      {!row.tagged && !row.has_blocking_issue && (
        <p className="import-row-note">
          Couldn&apos;t auto-tag this row. Add tags if you want, or save it without.
        </p>
      )}

      {row.issues.length > 0 && (
        <ul className="import-row-issues">
          {row.issues.map((code) => (
            <li key={code}>{ISSUE_LABELS[code] ?? code}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
