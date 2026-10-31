// src/features/session/SessionPage.jsx
import { useState } from 'react'
import { startSession } from '../../api/review'
import TopicGrid from '../topics/TopicGrid'
import { useTopicOverview } from '../topics/useTopicOverview'
import SessionRunner from './SessionRunner'
import { describeError } from './sessionErrors'
import { formatTopic } from './formatTopic'

export default function SessionPage() {
  const { overview, isLoading, error: overviewError, reload } = useTopicOverview()
  const [startedTopic, setStartedTopic] = useState(null) // null = all topics
  const [plan, setPlan] = useState(null)
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState(null)
  const [noDue, setNoDue] = useState(false)

  async function handleStart(topic) {
    if (isStarting) return
    setIsStarting(true)
    setError(null)
    setNoDue(false)
    setStartedTopic(topic)

    try {
      const data = await startSession(topic)
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

  function handleRestart() {
    setPlan(null)
    reload() // counts changed during the session, so refetch them
  }

  if (plan) {
    return <SessionRunner plan={plan} onRestart={handleRestart} />
  }

  return (
    <div className="scene-page">
      <h1>Review</h1>
      <p className="page-subtitle">
        Pick a topic to review inside a dialogue, or choose all topics to review sentences one by one.
      </p>

      <div className="filter-bar">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => handleStart(null)}
          disabled={isStarting}
        >
          {isStarting && startedTopic === null ? 'Preparing…' : 'Review all topics'}
        </button>
        {isStarting && startedTopic !== null && (
          <span>Preparing {formatTopic(startedTopic)}…</span>
        )}
      </div>

      {error && <p className="form-error">{error}</p>}

      {noDue && (
        <p className="empty-state">
          {startedTopic
            ? `Nothing due for "${formatTopic(startedTopic)}" right now — check back later.`
            : 'Nothing due right now — check back later.'}
        </p>
      )}

      {isLoading && <p className="page-subtitle">Loading your topics…</p>}

      {overviewError && (
        <p className="form-error">
          {overviewError}{' '}
          <button type="button" className="btn" onClick={reload}>
            Retry
          </button>
        </p>
      )}

      {!isLoading && !overviewError && (
        <TopicGrid overview={overview} onSelect={handleStart} />
      )}
    </div>
  )
}