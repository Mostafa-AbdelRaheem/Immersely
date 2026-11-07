// src/features/conversations/chatReducer.js
// Pure state logic for the chat page. No React, no fetch.

// Keep in sync with Settings.chat_max_history_messages on the backend:
// the server rejects longer histories with 422.
export const MAX_HISTORY_MESSAGES = 20

export const initialState = {
  messages: [], // { id, role: 'user' | 'partner', text, correction }
  chips: [], // { id, de, en }
  status: 'idle', // 'idle' | 'sending' | 'error'
  error: null,
  nextId: 1,
}

export function chatReducer(state, action) {
  switch (action.type) {
    case 'SEND_STARTED': {
      if (state.status === 'sending') return state
      const message = { id: state.nextId, role: 'user', text: action.text, correction: null }
      return {
        ...state,
        messages: [...state.messages, message],
        status: 'sending',
        error: null,
        nextId: state.nextId + 1,
      }
    }

    case 'OPENING_STARTED':
      if (state.status === 'sending') return state
      return { ...state, status: 'sending', error: null }

    case 'TURN_RECEIVED': {
      // Attach the correction to the most recent user message, if there is one.
      let lastUserIndex = -1
      state.messages.forEach((m, i) => {
        if (m.role === 'user') lastUserIndex = i
      })
      const messages = state.messages.map((m, i) =>
        i === lastUserIndex ? { ...m, correction: action.correction ?? null } : m,
      )
      messages.push({
        id: state.nextId,
        role: 'partner',
        text: action.reply,
        correction: null,
      })
      return {
        ...state,
        messages,
        chips: action.chips ?? [],
        status: 'idle',
        error: null,
        nextId: state.nextId + 1,
      }
    }

    case 'TURN_FAILED': {
      // Drop the unanswered learner message so a retry does not send it twice.
      const last = state.messages[state.messages.length - 1]
      const messages =
        last && last.role === 'user' ? state.messages.slice(0, -1) : state.messages
      return { ...state, messages, status: 'error', error: action.message }
    }

    case 'RESET':
      return initialState

    default:
      return state
  }
}

// The API wants [{ role, text }], oldest first, at most MAX_HISTORY_MESSAGES.
export function toHistory(messages) {
  return messages
    .slice(-MAX_HISTORY_MESSAGES)
    .map(({ role, text }) => ({ role, text }))
}