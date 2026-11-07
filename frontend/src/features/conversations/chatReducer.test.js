// src/features/conversations/chatReducer.test.js
import { describe, expect, it } from 'vitest'
import {
  MAX_HISTORY_MESSAGES,
  chatReducer,
  initialState,
  toHistory,
} from './chatReducer'

const chip = (n) => ({ id: `c${n}`, de: `de${n}`, en: `en${n}` })
const withMessages = (messages, nextId = messages.length + 1) => ({
  ...initialState,
  messages,
  nextId,
})
const user = (id, text = 'Hallo') => ({ id, role: 'user', text, correction: null })
const partner = (id, text = 'Hi') => ({ id, role: 'partner', text, correction: null })
const received = (over = {}) => ({
  type: 'TURN_RECEIVED',
  reply: 'Gerne!',
  correction: null,
  chips: [],
  ...over,
})

describe('SEND_STARTED', () => {
  it('appends the user message and marks the state as sending', () => {
    const next = chatReducer(initialState, { type: 'SEND_STARTED', text: 'Ich bin müde' })
    expect(next.messages).toEqual([
      { id: 1, role: 'user', text: 'Ich bin müde', correction: null },
    ])
    expect(next.status).toBe('sending')
    expect(next.nextId).toBe(2)
  })

  it('is ignored while a request is already running', () => {
    const sending = { ...initialState, status: 'sending' }
    expect(chatReducer(sending, { type: 'SEND_STARTED', text: 'x' })).toBe(sending)
  })

  it('clears a previous error', () => {
    const failed = { ...initialState, status: 'error', error: 'boom' }
    const next = chatReducer(failed, { type: 'SEND_STARTED', text: 'x' })
    expect(next.error).toBeNull()
  })
})

describe('OPENING_STARTED', () => {
  it('sets sending without adding a message', () => {
    const next = chatReducer(initialState, { type: 'OPENING_STARTED' })
    expect(next.status).toBe('sending')
    expect(next.messages).toEqual([])
  })

  it('is ignored while a request is already running', () => {
    const sending = { ...initialState, status: 'sending' }
    expect(chatReducer(sending, { type: 'OPENING_STARTED' })).toBe(sending)
  })
})

describe('TURN_RECEIVED', () => {
  it('appends the partner message and returns to idle', () => {
    const state = { ...withMessages([user(1)]), status: 'sending' }
    const next = chatReducer(state, received({ reply: 'Gerne!' }))
    expect(next.messages[1]).toEqual({
      id: 2,
      role: 'partner',
      text: 'Gerne!',
      correction: null,
    })
    expect(next.status).toBe('idle')
  })

  it('attaches the correction to the last user message only', () => {
    const state = withMessages([user(1), partner(2), user(3)])
    const correction = { verdict: 'fixable_errors', corrected_text: 'x', note: 'n' }
    const next = chatReducer(state, received({ correction }))
    expect(next.messages[0].correction).toBeNull()
    expect(next.messages[2].correction).toEqual(correction)
  })

  it('handles the opening turn: only a partner message, nothing to correct', () => {
    const next = chatReducer(initialState, received({ reply: 'Willkommen!' }))
    expect(next.messages).toHaveLength(1)
    expect(next.messages[0].role).toBe('partner')
  })

  it('turns a missing correction into null', () => {
    const state = withMessages([user(1)])
    const next = chatReducer(state, { type: 'TURN_RECEIVED', reply: 'Ok', chips: [] })
    expect(next.messages[0].correction).toBeNull()
  })

  it('replaces the previous chips', () => {
    const state = { ...withMessages([user(1)]), chips: [chip(1)] }
    const next = chatReducer(state, received({ chips: [chip(2), chip(3)] }))
    expect(next.chips).toEqual([chip(2), chip(3)])
  })
})

describe('TURN_FAILED', () => {
  it('removes the unanswered user message and stores the error', () => {
    const state = { ...withMessages([partner(1), user(2)]), status: 'sending' }
    const next = chatReducer(state, { type: 'TURN_FAILED', message: 'busy' })
    expect(next.messages).toEqual([partner(1)])
    expect(next.status).toBe('error')
    expect(next.error).toBe('busy')
  })

  it('keeps the messages when the last one is not from the learner', () => {
    const state = { ...withMessages([partner(1)]), status: 'sending' }
    const next = chatReducer(state, { type: 'TURN_FAILED', message: 'busy' })
    expect(next.messages).toEqual([partner(1)])
  })

  it('allows sending again after a failure', () => {
    const failed = chatReducer(
      { ...withMessages([user(1)]), status: 'sending' },
      { type: 'TURN_FAILED', message: 'busy' },
    )
    const next = chatReducer(failed, { type: 'SEND_STARTED', text: 'Nochmal' })
    expect(next.status).toBe('sending')
  })
})

describe('RESET and unknown actions', () => {
  it('RESET returns the initial state', () => {
    const state = { ...withMessages([user(1)]), chips: [chip(1)], status: 'error' }
    expect(chatReducer(state, { type: 'RESET' })).toEqual(initialState)
  })

  it('returns the same state for an unknown action', () => {
    expect(chatReducer(initialState, { type: 'NOPE' })).toBe(initialState)
  })

  it('does not mutate the state it receives', () => {
    const state = withMessages([user(1)])
    const before = JSON.stringify(state)
    chatReducer(state, received({ correction: { verdict: 'valid' } }))
    expect(JSON.stringify(state)).toBe(before)
  })
})

describe('toHistory', () => {
  it('keeps only role and text', () => {
    const messages = [{ ...user(1, 'Hi'), correction: { verdict: 'valid' } }]
    expect(toHistory(messages)).toEqual([{ role: 'user', text: 'Hi' }])
  })

  it('keeps only the last MAX_HISTORY_MESSAGES, newest included', () => {
    const messages = Array.from({ length: MAX_HISTORY_MESSAGES + 5 }, (_, i) =>
      user(i + 1, `m${i + 1}`),
    )
    const history = toHistory(messages)
    expect(history).toHaveLength(MAX_HISTORY_MESSAGES)
    expect(history[history.length - 1].text).toBe(`m${MAX_HISTORY_MESSAGES + 5}`)
  })

  it('returns an empty list for no messages', () => {
    expect(toHistory([])).toEqual([])
  })
})