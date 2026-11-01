// src/features/session/flipReducer.js
// Pure flip-card session state machine: no React, no network, no clock.
// `now` (ms since epoch) is always passed in via the action.

export const PHASE = Object.freeze({
  FRONT: 'front',
  BACK: 'back',
  SAVING: 'saving',
  SUMMARY: 'summary',
})

// A graded card whose next due time is within this window of "now" goes back
// into this session's queue (e.g. "Again" is scheduled 10 minutes out). The
// extra slack covers small clock differences between browser and server.
export const REQUEUE_WINDOW_MINUTES = 15

const GRADES = ['again', 'hard', 'good', 'easy']

// cards = the `cards` array from POST /review/flip/start
export function createInitialState(cards) {
  return {
    queue: [...cards],
    phase: cards.length > 0 ? PHASE.FRONT : PHASE.SUMMARY,
    results: [],
    pendingGrade: null,
    error: null,
  }
}

export function currentCard(state) {
  return state.queue[0] ?? null
}

export function cardsLeft(state) {
  return state.queue.length
}

function shouldRequeue(srsDue, nowMs) {
  const dueMs = Date.parse(srsDue)
  if (Number.isNaN(dueMs)) return false
  return dueMs - nowMs <= REQUEUE_WINDOW_MINUTES * 60 * 1000
}

export function flipReducer(state, action) {
  switch (action.type) {
    case 'revealed':
      if (state.phase !== PHASE.FRONT) return state
      return { ...state, phase: PHASE.BACK, error: null }

    case 'flipped_back':
      // Look at the question again. Not allowed while a grade is saving.
      if (state.phase !== PHASE.BACK) return state
      return { ...state, phase: PHASE.FRONT, error: null }

    case 'grade_selected':
      if (state.phase !== PHASE.BACK) return state
      if (!GRADES.includes(action.grade)) return state
      return { ...state, phase: PHASE.SAVING, pendingGrade: action.grade, error: null }

    case 'grade_failed':
      if (state.phase !== PHASE.SAVING) return state
      return { ...state, phase: PHASE.BACK, pendingGrade: null, error: action.message }

    case 'grade_succeeded': {
      if (state.phase !== PHASE.SAVING) return state
      const [card, ...rest] = state.queue
      const requeued = shouldRequeue(action.saved.srs_due, action.now)
      const queue = requeued ? [...rest, card] : rest
      const result = {
        sentenceId: card.sentence_id,
        grade: state.pendingGrade,
        srsDue: action.saved.srs_due,
        srsState: action.saved.srs_state,
        requeued,
      }
      return {
        ...state,
        queue,
        results: [...state.results, result],
        phase: queue.length > 0 ? PHASE.FRONT : PHASE.SUMMARY,
        pendingGrade: null,
        error: null,
      }
    }

    case 'ended_early':
      // Only between cards. While saving, a grade is in flight.
      if (state.phase !== PHASE.FRONT && state.phase !== PHASE.BACK) return state
      return { ...state, phase: PHASE.SUMMARY, pendingGrade: null, error: null }

    default:
      return state
  }
}

// results can contain the same card twice (re-queued), so count both ways.
export function buildSummary(results) {
  const grades = { again: 0, hard: 0, good: 0, easy: 0 }
  const lastByCard = new Map()
  for (const r of results) {
    grades[r.grade] += 1
    lastByCard.set(r.sentenceId, r) // later results overwrite earlier ones
  }

  let nextDue = null
  for (const r of lastByCard.values()) {
    if (nextDue === null || Date.parse(r.srsDue) < Date.parse(nextDue)) {
      nextDue = r.srsDue
    }
  }

  return {
    reviews: results.length,
    cards: lastByCard.size,
    grades,
    nextDue,
  }
}