// src/features/sentences/TagEditor.jsx
import { useState } from 'react'
import { useTopics } from '../../context/TopicsContext'

export default function TagEditor({ sentence, onUpdate }) {
  const { topics: allTopics } = useTopics()
  const [grammarTagDraft, setGrammarTagDraft] = useState(sentence.grammar_tag ?? '')

  const currentTopics = sentence.topics
  const availableToAdd = allTopics.filter((t) => !currentTopics.includes(t))

  async function handleRemoveTopic(topic) {
    await onUpdate(sentence.id, {
      topics: currentTopics.filter((t) => t !== topic),
    })
  }

  async function handleAddTopic(e) {
    const topic = e.target.value
    if (!topic) return
    await onUpdate(sentence.id, {
      topics: [...currentTopics, topic],
    })
    e.target.value = ''
  }

  async function handleGrammarTagCommit() {
    const trimmed = grammarTagDraft.trim()
    if (trimmed === (sentence.grammar_tag ?? '')) return
    await onUpdate(sentence.id, {
      grammar_tag: trimmed || null,
    })
  }

  return (
    <div className="tag-editor">
      {currentTopics.map((t) => (
        <span className="tag-chip" key={t}>
          {t}
          <button type="button" onClick={() => handleRemoveTopic(t)} aria-label={`Remove ${t}`}>
            ×
          </button>
        </span>
      ))}

      {availableToAdd.length > 0 && (
        <select className="tag-add-select" defaultValue="" onChange={handleAddTopic}>
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
        value={grammarTagDraft}
        onChange={(e) => setGrammarTagDraft(e.target.value)}
        onBlur={handleGrammarTagCommit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') e.target.blur()
        }}
        placeholder="grammar tag"
      />
    </div>
  )
}