// src/features/session/sessionReducer.js
// Pure review-session state machine: no React, no network.

export const PHASE = Object.freeze({
  ANSWERING: 'answering',
  CHECKING: 'checking',
  FEEDBACK: 'feedback',
  SAVING: 'saving',
  CLOSING: 'closing',
  SUMMARY: 'summary',
})

const GRADES = ['again', 'hard', 'good', 'easy']

function enterChunk(state, index) {
  const blank = {
    answer: '',
    checkResult: null,
    selectedGrade: null,
    hintRevealed: false,
    error: null,
  }
  const chunk = state.plan.chunks[index]
  if (!chunk) {
    return { ...state, ...blank, chunkIndex: index, phase: PHASE.SUMMARY }
  }
  return {
    ...state,
    ...blank,
    chunkIndex: index,
    phase: chunk.target ? PHASE.ANSWERING : PHASE.CLOSING,
  }
}

// plan = the POST /review/session/start response
export function createInitialState(plan) {
  return enterChunk({ plan, results: [], chunkIndex: 0 }, 0)
}

export function currentChunk(state) {
  return state.plan.chunks[state.chunkIndex] ?? null
}

// Scene mode: English hidden until "Show hint". Isolated mode: English is the cue.
export function isHintVisible(state) {
  return state.plan.mode === 'isolated' || state.hintRevealed
}

// Exactly what gradeReview(sentenceId, payload) expects.
export function buildGradePayload(state) {
  return {
    grade: state.selectedGrade,
    tier: state.checkResult.tier,
    userInput: state.answer,
    correctedInput: state.checkResult.corrected_input ?? null,
    rulePracticed: state.checkResult.rule_practiced ?? null,
    sceneId: state.plan.scene_id ?? null,
  }
}

export function buildSummary(results) {
  const tiers = { correct: 0, almost_correct: 0, incorrect: 0 }
  const grades = { again: 0, hard: 0, good: 0, easy: 0 }
  let nextDue = null
  for (const r of results) {
    tiers[r.tier] += 1
    grades[r.grade] += 1
    if (nextDue === null || new Date(r.srsDue) < new Date(nextDue)) {
      nextDue = r.srsDue
    }
  }
  return {
    total: results.length,
    tiers,
    grades,
    overrides: results.filter((r) => r.overridden).length,
    nextDue,
  }
}

export function sessionReducer(state, action) {
  switch (action.type) {
    case 'hint_revealed':
      if (state.phase !== PHASE.ANSWERING) return state
      return { ...state, hintRevealed: true }

    case 'submitted': {
      if (state.phase !== PHASE.ANSWERING) return state
      const answer = (action.answer ?? '').trim()
      if (!answer) return state
      return { ...state, phase: PHASE.CHECKING, answer, error: null }
    }

    case 'check_succeeded':
      if (state.phase !== PHASE.CHECKING) return state
      return {
        ...state,
        phase: PHASE.FEEDBACK,
        checkResult: action.result,
        selectedGrade: action.result.suggested_grade,
        error: null,
      }

    case 'check_failed':
      if (state.phase !== PHASE.CHECKING) return state
      return { ...state, phase: PHASE.ANSWERING, error: action.message }

    case 'grade_selected':
      if (state.phase !== PHASE.FEEDBACK) return state
      if (!GRADES.includes(action.grade)) return state
      return { ...state, selectedGrade: action.grade }

    case 'continue_started':
      if (state.phase !== PHASE.FEEDBACK) return state
      return { ...state, phase: PHASE.SAVING, error: null }

    case 'grade_failed':
      if (state.phase !== PHASE.SAVING) return state
      return { ...state, phase: PHASE.FEEDBACK, error: action.message }

    case 'grade_succeeded': {
      if (state.phase !== PHASE.SAVING) return state
      const chunk = currentChunk(state)
      const check = state.checkResult
      const result = {
        sentenceId: chunk.target.sentence_id,
        tier: check.tier,
        suggestedGrade: check.suggested_grade,
        grade: state.selectedGrade,
        overridden: state.selectedGrade !== check.suggested_grade,
        userInput: state.answer,
        srsDue: action.saved.srs_due,
        srsState: action.saved.srs_state,
      }
      return enterChunk(
        { ...state, results: [...state.results, result] },
        state.chunkIndex + 1,
      )
    }

    case 'finished':
      if (state.phase !== PHASE.CLOSING) return state
      return enterChunk(state, state.plan.chunks.length)

    default:
      return state
  }
}