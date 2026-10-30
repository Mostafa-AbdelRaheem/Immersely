// src/features/session/SessionPage.jsx
import { useState } from 'react'
import { startSession } from '../../api/review'
import { useTopics } from '../../context/TopicsContext'
import SessionRunner from './SessionRunner'
import { describeError } from './sessionErrors'

export default function SessionPage() {
  const { topics, isLoading: topicsLoading } = useTopics()
  const [selectedTopic, setSelectedTopic] = useState('') // '' = all topics
  const [plan, setPlan] = useState(null)
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState(null)
  const [noDue, setNoDue] = useState(false)

  async function handleStart() {
    setIsStarting(true)
    setError(null)
    setNoDue(false)

    try {
      const data = await startSession(selectedTopic || null)
      setPlan(data)
    } catch (err) {
      if (err.status === 404) {
        setNoDue(true)
      } else {
        setError(
          describeError(err, 'Could not prepare the review session right now. Please try again.'),
        )
      }
    } finally {
      setIsStarting(false)
    }
  }

  if (plan) {
    return <SessionRunner plan={plan} onRestart={() => setPlan(null)} />
  }

  return (
    <div className="scene-page">
      <h1>Review</h1>
      <p className="page-subtitle">
        Pick a topic to review inside a dialogue, or choose all topics to review sentences one by one.
      </p>

      <div className="filter-bar">
        <label htmlFor="session-topic">Topic:</label>
        <select
          id="session-topic"
          value={selectedTopic}
          onChange={(e) => setSelectedTopic(e.target.value)}
          disabled={topicsLoading || isStarting}
        >
          <option value="">All topics</option>
          {topics.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleStart}
          disabled={topicsLoading || isStarting}
        >
          {isStarting ? 'Preparing…' : 'Start review'}
        </button>
      </div>

      {error && <p className="form-error">{error}</p>}

      {noDue && (
        <p className="empty-state">
          {selectedTopic
            ? `Nothing due for "${selectedTopic}" right now — check back later.`
            : 'Nothing due right now — check back later.'}
        </p>
      )}
    </div>
  )
}