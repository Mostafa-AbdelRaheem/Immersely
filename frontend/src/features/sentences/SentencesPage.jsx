// src/features/sentences/SentencesPage.jsx
import { useEffect, useState } from 'react'
import { listSentences, createSentence, updateSentence, deleteSentence } from '../../api/sentences'
import SentenceForm from './SentenceForm'
import SentenceListItem from './SentenceListItem'

export default function SentencesPage() {
  const [sentences, setSentences] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

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
  }, [])

  async function handleCreate(data) {
    const newSentence = await createSentence(data)
    setSentences((prev) => [newSentence, ...prev])
  }

  async function handleUpdate(id, changes) {
    const updated = await updateSentence(id, changes)
    setSentences((prev) => prev.map((s) => (s.id === id ? updated : s)))
  }

  async function handleDelete(id) {
    await deleteSentence(id)
    setSentences((prev) => prev.filter((s) => s.id !== id))
  }

  if (isLoading) return <p>Loading…</p>
  if (error) return <p style={{ color: 'red' }}>{error}</p>

  return (
    <div>
      <h1>My Sentences</h1>

      <SentenceForm onSubmit={handleCreate} submitLabel="Add sentence" />

      {sentences.length === 0 ? (
        <p>No sentences yet — add one above.</p>
      ) : (
        <div>
          {sentences.map((s) => (
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