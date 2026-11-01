// src/features/session/flipReducer.test.js
import { describe, expect, it } from 'vitest'
import {
  PHASE,
  REQUEUE_WINDOW_MINUTES,
  buildSummary,
  cardsLeft,
  createInitialState,
  currentCard,
  flipReducer,
} from './flipReducer'

const NOW = Date.parse('2026-11-01T10:00:00Z')
const card = (n) => ({ sentence_id: `s${n}`, de: `de${n}`, en: `en${n}` })
const saved = (minutes) => ({
  srs_due: new Date(NOW + minutes * 60 * 1000).toISOString(),
  srs_state: 'learning',
})

function run(state, ...actions) {
  return actions.reduce(flipReducer, state)
}

// reveal -> grade -> server answers with a due time `minutes` from NOW
function gradeCard(state, grade, minutes) {
  return run(
    state,
    { type: 'revealed' },
    { type: 'grade_selected', grade },
    { type: 'grade_succeeded', saved: saved(minutes), now: NOW },
  )
}

const DAY = 24 * 60

describe('createInitialState', () => {
  it('starts on the front of the first card', () => {
    const s = createInitialState([card(1), card(2)])
    expect(s.phase).toBe(PHASE.FRONT)
    expect(currentCard(s).sentence_id).toBe('s1')
    expect(cardsLeft(s)).toBe(2)
  })

  it('goes straight to the summary when there are no cards', () => {
    expect(createInitialState([]).phase).toBe(PHASE.SUMMARY)
  })
})

describe('reveal and grade selection', () => {
  it('reveal moves front to back', () => {
    const s = run(createInitialState([card(1)]), { type: 'revealed' })
    expect(s.phase).toBe(PHASE.BACK)
  })

  it('reveal is ignored outside the front phase', () => {
    const back = run(createInitialState([card(1)]), { type: 'revealed' })
    expect(flipReducer(back, { type: 'revealed' })).toBe(back)
  })

  it('selecting a grade on the back moves to saving', () => {
    const s = run(
      createInitialState([card(1)]),
      { type: 'revealed' },
      { type: 'grade_selected', grade: 'good' },
    )
    expect(s.phase).toBe(PHASE.SAVING)
    expect(s.pendingGrade).toBe('good')
  })

  it('ignores an unknown grade and grading before the reveal', () => {
    const front = createInitialState([card(1)])
    expect(flipReducer(front, { type: 'grade_selected', grade: 'good' })).toBe(front)
    const back = flipReducer(front, { type: 'revealed' })
    expect(flipReducer(back, { type: 'grade_selected', grade: 'perfect' })).toBe(back)
  })
})

describe('re-queue rule', () => {
  it('a card due far in the future is finished for this session', () => {
    const s = gradeCard(createInitialState([card(1), card(2)]), 'good', DAY)
    expect(cardsLeft(s)).toBe(1)
    expect(currentCard(s).sentence_id).toBe('s2')
    expect(s.results[0].requeued).toBe(false)
  })

  it('a card due in 10 minutes goes to the back of the queue', () => {
    const s = gradeCard(createInitialState([card(1), card(2)]), 'again', 10)
    expect(s.queue.map((c) => c.sentence_id)).toEqual(['s2', 's1'])
    expect(s.results[0].requeued).toBe(true)
    expect(s.phase).toBe(PHASE.FRONT)
  })

  it('re-queues exactly at the window edge but not one minute past it', () => {
    const start = createInitialState([card(1), card(2)])
    const atEdge = gradeCard(start, 'hard', REQUEUE_WINDOW_MINUTES)
    expect(cardsLeft(atEdge)).toBe(2)
    const pastEdge = gradeCard(start, 'hard', REQUEUE_WINDOW_MINUTES + 1)
    expect(cardsLeft(pastEdge)).toBe(1)
  })

  it('finishing the last card shows the summary', () => {
    const s = gradeCard(createInitialState([card(1)]), 'good', DAY)
    expect(s.phase).toBe(PHASE.SUMMARY)
  })

  it('failing the last card keeps it in the queue', () => {
    const s = gradeCard(createInitialState([card(1)]), 'again', 10)
    expect(s.phase).toBe(PHASE.FRONT)
    expect(currentCard(s).sentence_id).toBe('s1')
  })
})

describe('saving errors', () => {
  it('a failed save returns to the back with a message and keeps the queue', () => {
    const s = run(
      createInitialState([card(1)]),
      { type: 'revealed' },
      { type: 'grade_selected', grade: 'good' },
      { type: 'grade_failed', message: 'nope' },
    )
    expect(s.phase).toBe(PHASE.BACK)
    expect(s.error).toBe('nope')
    expect(s.pendingGrade).toBeNull()
    expect(cardsLeft(s)).toBe(1)
    expect(s.results).toHaveLength(0)
  })
})

describe('ending early', () => {
  it('works from the front and from the back', () => {
    const front = createInitialState([card(1), card(2)])
    expect(flipReducer(front, { type: 'ended_early' }).phase).toBe(PHASE.SUMMARY)
    const back = flipReducer(front, { type: 'revealed' })
    expect(flipReducer(back, { type: 'ended_early' }).phase).toBe(PHASE.SUMMARY)
  })

  it('is ignored while a grade is being saved and after the summary', () => {
    const saving = run(
      createInitialState([card(1)]),
      { type: 'revealed' },
      { type: 'grade_selected', grade: 'good' },
    )
    expect(flipReducer(saving, { type: 'ended_early' })).toBe(saving)
    const done = gradeCard(createInitialState([card(1)]), 'good', DAY)
    expect(flipReducer(done, { type: 'ended_early' })).toBe(done)
  })

  it('keeps the grades saved so far', () => {
    const afterOne = gradeCard(createInitialState([card(1), card(2)]), 'good', DAY)
    const ended = flipReducer(afterOne, { type: 'ended_early' })
    expect(ended.results).toHaveLength(1)
  })
})

describe('purity', () => {
  it('does not mutate the previous state', () => {
    const start = createInitialState([card(1), card(2)])
    const snapshot = JSON.stringify(start)
    gradeCard(start, 'again', 10)
    expect(JSON.stringify(start)).toBe(snapshot)
  })
})

describe('buildSummary', () => {
  it('counts reviews, distinct cards, grades and the earliest next due', () => {
    let s = createInitialState([card(1), card(2)])
    s = gradeCard(s, 'again', 10) // s1 comes back
    s = gradeCard(s, 'good', DAY) // s2 done
    s = gradeCard(s, 'good', 3 * DAY) // s1 done on its second review
    const summary = buildSummary(s.results)
    expect(summary.reviews).toBe(3)
    expect(summary.cards).toBe(2)
    expect(summary.grades).toEqual({ again: 1, hard: 0, good: 2, easy: 0 })
    // s1's LAST result (3 days) and s2's (1 day) -> earliest is s2's
    expect(summary.nextDue).toBe(saved(DAY).srs_due)
  })

  it('handles an empty session', () => {
    const summary = buildSummary([])
    expect(summary.reviews).toBe(0)
    expect(summary.nextDue).toBeNull()
  })
})