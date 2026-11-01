// src/features/session/FlipRunner.jsx
import { useReducer } from 'react'
import { gradeFlip } from '../../api/review'
import { useDueCount } from '../../context/DueCountContext'
import FlipCard from './FlipCard'
import FlipSummary from './FlipSummary'
import GradeChips from './GradeChips'
import { describeError } from './sessionErrors'
import {
  PHASE,
  buildSummary,
  cardsLeft,
  createInitialState,
  currentCard,
  flipReducer,
} from './flipReducer'
import { formatTopic } from './formatTopic'
import './SessionRunner.css'

export default function FlipRunner({ cards, topic, direction, onRestart }) {
  const [state, dispatch] = useReducer(flipReducer, cards, createInitialState)
  const { refresh: refreshDueCount } = useDueCount()

  if (state.phase === PHASE.SUMMARY) {
    return <FlipSummary summary={buildSummary(state.results)} onRestart={onRestart} />
  }

  const card = currentCard(state)
  const saving = state.phase === PHASE.SAVING
  const showChips = state.phase === PHASE.BACK || saving

  function handleFlip() {
    if (state.phase === PHASE.FRONT) {
      dispatch({ type: 'revealed' })
    } else if (state.phase === PHASE.BACK) {
      dispatch({ type: 'flipped_back' })
    }
  }

  async function handleGrade(grade) {
    if (state.phase !== PHASE.BACK) return

    dispatch({ type: 'grade_selected', grade })
    try {
      const saved = await gradeFlip(card.sentence_id, grade)
      dispatch({ type: 'grade_succeeded', saved, now: Date.now() })
      refreshDueCount() // fire-and-forget: it never throws, and must not block the UI
    } catch (err) {
      dispatch({
        type: 'grade_failed',
        message: describeError(err, 'Could not save your grade. Please try again.'),
      })
    }
  }

  return (
    <div className="session-runner">
      <div className="scene-header">
        <span className="scene-topic">{topic ? formatTopic(topic) : 'All topics'}</span>
        <span className="scene-meta">{cardsLeft(state)} left</span>
      </div>

      <FlipCard
        key={`${card.sentence_id}-${state.results.length}`}
        card={card}
        direction={direction}
        revealed={showChips}
        disabled={saving}
        onFlip={handleFlip}
      />

      {showChips && (
        <div className="session-feedback">
          <GradeChips
            selected={state.pendingGrade}
            suggested={null}
            disabled={saving}
            onSelect={handleGrade}
          />
          {state.error && <p className="form-error">{state.error}</p>}
        </div>
      )}

      <button
        type="button"
        className="btn btn-secondary"
        disabled={saving}
        onClick={() => dispatch({ type: 'ended_early' })}
      >
        End session
      </button>
    </div>
  )
}