// src/features/sentences/SentencesPage.jsx
import { useEffect, useState } from 'react'
import { listSentences, updateSentence, deleteSentence } from '../../api/sentences'
import { useSentencesSync } from '../../context/SentencesSyncContext'
import { useTopics } from '../../context/TopicsContext'
import SentenceListItem from './SentenceListItem'
import './sentences.css'

export default function SentencesPage() {
  const [sentences, setSentences] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedTopic, setSelectedTopic] = useState(null)

  const { topics } = useTopics()
  // Bumped by the global add modal; refetching on change keeps this list current.
  const { sentencesVersion } = useSentencesSync()

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const data = await listSentences()
        if (!cancelled) {
          setSentences(data)
        }
      } catch (err) {
        if (!cancelled) {
          setError('Failed to load sentences.')
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    load()

    return () => {
      cancelled = true
    }
  }, [sentencesVersion])

  async function handleUpdate(id, changes) {
    const updated = await updateSentence(id, changes)
    setSentences((prev) => prev.map((s) => (s.id === id ? updated : s)))
  }

  async function handleDelete(id) {
    await deleteSentence(id)
    setSentences((prev) => prev.filter((s) => s.id !== id))
  }

  if (isLoading) return <p>Loading…</p>
  if (error) return <p className="form-error">{error}</p>

  const filteredSentences = selectedTopic
    ? sentences.filter((s) => s.topics.includes(selectedTopic))
    : sentences

  return (
    <div>
      <h1>Cards</h1>

      <div className="filter-bar">
        <label htmlFor="topic-filter">Filter by topic:</label>
        <select
          id="topic-filter"
          value={selectedTopic ?? ''}
          onChange={(e) => setSelectedTopic(e.target.value || null)}
        >
          <option value="">All topics</option>
          {topics.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {filteredSentences.length === 0 ? (
        <p className="empty-state">
          {sentences.length === 0
            ? 'No cards yet. Tap the + button to add one.'
            : 'No sentences match this topic.'}
        </p>
      ) : (
        <div className="sentence-list">
          {filteredSentences.map((s) => (
            <SentenceListItem
              key={s.id}
              sentence={s}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}