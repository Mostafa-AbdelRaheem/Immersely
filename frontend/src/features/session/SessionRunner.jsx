// src/features/session/SessionRunner.jsx
import { useReducer } from 'react'
import { checkAnswer, gradeReview } from '../../api/review'
import ChunkView from './ChunkView'
import CorrectionFeedback from './CorrectionFeedback'
import GradeChips from './GradeChips'
import SessionSummary from './SessionSummary'
import { describeError } from './sessionErrors'
import {
  PHASE,
  buildGradePayload,
  buildSummary,
  createInitialState,
  currentChunk,
  isHintVisible,
  sessionReducer,
} from './sessionReducer'
import { formatDueIn } from './formatDue'
import { formatTopic } from './formatTopic'
import './SessionRunner.css'

export default function SessionRunner({ plan, onRestart }) {
  const [state, dispatch] = useReducer(sessionReducer, plan, createInitialState)

  if (state.phase === PHASE.SUMMARY) {
    return <SessionSummary summary={buildSummary(state.results)} onRestart={onRestart} />
  }

  const chunk = currentChunk(state)
  const totalTargets = plan.chunks.filter((c) => c.target).length
  const showFeedback = state.phase === PHASE.FEEDBACK || state.phase === PHASE.SAVING
  const saving = state.phase === PHASE.SAVING
  const lastResult = state.results[state.results.length - 1]

  async function handleSubmit(text) {
    if (state.phase !== PHASE.ANSWERING) return
    const answer = text.trim()
    if (!answer) return

    dispatch({ type: 'submitted', answer })
    try {
      const result = await checkAnswer(chunk.target.sentence_id, answer)
      dispatch({ type: 'check_succeeded', result })
    } catch (err) {
      dispatch({
        type: 'check_failed',
        message: describeError(err, 'Could not check your answer right now. Please try again.'),
      })
    }
  }

  async function handleContinue() {
    if (state.phase !== PHASE.FEEDBACK) return

    const payload = buildGradePayload(state)
    dispatch({ type: 'continue_started' })
    try {
      const saved = await gradeReview(chunk.target.sentence_id, payload)
      dispatch({ type: 'grade_succeeded', saved })
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
        <span className="scene-topic">
          {plan.mode === 'scene' ? formatTopic(plan.topic) : 'All topics'}
        </span>
        <span className="scene-meta">
          {state.results.length} of {totalTargets} reviewed
        </span>
      </div>
      {lastResult && state.phase !== PHASE.FEEDBACK && state.phase !== PHASE.SAVING && (
        <p className="session-saved">
          Saved: {lastResult.grade} · next review {formatDueIn(lastResult.srsDue)}
        </p>
      )}
      <ChunkView
        key={state.chunkIndex}
        chunk={chunk}
        mode={plan.mode}
        phase={state.phase}
        hintVisible={isHintVisible(state)}
        error={state.phase === PHASE.ANSWERING ? state.error : null}
        onRevealHint={() => dispatch({ type: 'hint_revealed' })}
        onSubmit={handleSubmit}
        onFinish={() => dispatch({ type: 'finished' })}
      />

      {showFeedback && (
        <div className="session-feedback">
          <CorrectionFeedback result={state.checkResult} />
          <GradeChips
            selected={state.selectedGrade}
            suggested={state.checkResult.suggested_grade}
            disabled={saving}
            onSelect={(grade) => dispatch({ type: 'grade_selected', grade })}
          />
          {state.error && <p className="form-error">{state.error}</p>}
          <button
            type="button"
            className="btn btn-primary"
            disabled={saving}
            onClick={handleContinue}
          >
            {saving ? 'Saving…' : 'Continue'}
          </button>
        </div>
      )}
    </div>
  )
}