// src/features/session/SessionPage.jsx
import { useState } from 'react'
import { startFlipSession, startSession } from '../../api/review'
import { useDueCount } from '../../context/DueCountContext'
import TopicGrid from '../topics/TopicGrid'
import { useTopicOverview } from '../topics/useTopicOverview'
import FlipRunner from './FlipRunner'
import MethodPanel from './MethodPanel'
import SessionRunner from './SessionRunner'
import { describeError } from './sessionErrors'
import { formatTopic } from './formatTopic'

export default function SessionPage() {
  const { overview, isLoading, error: overviewError, reload } = useTopicOverview()
  const { count: totalDue } = useDueCount()

  // null = nothing chosen yet; { topic: null } = all topics; { topic: 'x' } = one topic
  const [selection, setSelection] = useState(null)
  const [plan, setPlan] = useState(null) // typed or scene session
  const [flip, setFlip] = useState(null) // { cards, topic, direction }
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState(null)
  const [noDue, setNoDue] = useState(false)

  function handleSelect(topic) {
    if (isStarting) return
    setSelection({ topic })
    setError(null)
    setNoDue(false)
  }

  async function handleStart({ method, direction, limit }) {
    if (isStarting || !selection) return
    const { topic } = selection
    setIsStarting(true)
    setError(null)
    setNoDue(false)

    try {
      if (method === 'flip') {
        const data = await startFlipSession(topic, limit)
        setFlip({ cards: data.cards, topic, direction })
      } else {
        setPlan(await startSession(topic, undefined, method))
      }
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
    setFlip(null)
    reload() // counts changed during the session, so refetch them
  }

  if (flip) {
    return (
      <FlipRunner
        cards={flip.cards}
        topic={flip.topic}
        direction={flip.direction}
        onRestart={handleRestart}
      />
    )
  }

  if (plan) {
    return <SessionRunner plan={plan} onRestart={handleRestart} />
  }

  const selectedDue = selection
    ? selection.topic === null
      ? totalDue ?? 0
      : overview.find((t) => t.topic === selection.topic)?.due_count ?? 0
    : 0

  return (
    <div className="scene-page">
      <h1>Review</h1>
      <p className="page-subtitle">
        Pick a topic, or all topics, then choose how you want to study.
      </p>

      <div className="filter-bar">
        <button
          type="button"
          className="btn btn-secondary"
          aria-pressed={selection !== null && selection.topic === null}
          onClick={() => handleSelect(null)}
          disabled={isStarting}
        >
          All topics
        </button>
      </div>

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
        <TopicGrid overview={overview} onSelect={handleSelect} />
      )}

      {selection && (
        <MethodPanel
          key={`${selection.topic ?? '__all__'}-${selectedDue}`}
          topic={selection.topic}
          dueCount={selectedDue}
          isStarting={isStarting}
          onStart={handleStart}
        />
      )}

      {error && <p className="form-error">{error}</p>}

      {noDue && (
        <p className="empty-state">
          {selection?.topic
            ? `Nothing due for "${formatTopic(selection.topic)}" right now — check back later.`
            : 'Nothing due right now — check back later.'}
        </p>
      )}
    </div>
  )
}