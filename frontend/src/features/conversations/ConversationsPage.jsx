// src/features/conversations/ConversationsPage.jsx
import { useEffect, useReducer, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useOutletContext } from 'react-router-dom'
import { listScenarios, sendTurn } from '../../api/conversations'
import ChatMessage from './ChatMessage'
import ChipRow from './ChipRow'
import { chatReducer, initialState, toHistory } from './chatReducer'
import './ConversationsPage.css'

const MAX_MESSAGE_CHARS = 500 // keep in sync with Settings.chat_max_message_chars

function errorMessage(err) {
  if (err.status === 429) return 'You are sending messages too fast. Wait a moment.'
  if (err.status === 503) return 'The chat service is busy. Please try again.'
  return 'Could not get a reply right now. Please try again.'
}

export default function ConversationsPage() {
  const { topbarSlot } = useOutletContext()
  const [scenarios, setScenarios] = useState([])
  const [scenariosError, setScenariosError] = useState(null)
  const [scenario, setScenario] = useState(null)
  const [state, dispatch] = useReducer(chatReducer, initialState)
  const [draft, setDraft] = useState('')
  const requestId = useRef(0)
  const endRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const data = await listScenarios()
        if (!cancelled) setScenarios(data)
      } catch {
        if (!cancelled) setScenariosError('Could not load the scenarios. Please try again.')
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [state.messages.length, state.status])

  async function runTurn(scenarioId, history) {
    const id = ++requestId.current
    try {
      const result = await sendTurn(scenarioId, history)
      if (id !== requestId.current) return false // a newer request replaced this one
      dispatch({
        type: 'TURN_RECEIVED',
        reply: result.partner_reply,
        correction: result.correction,
        chips: result.chips,
      })
      return true
    } catch (err) {
      if (id !== requestId.current) return false
      dispatch({ type: 'TURN_FAILED', message: errorMessage(err) })
      return false
    }
  }

  function handlePick(s) {
    setScenario(s)
    setDraft('')
    dispatch({ type: 'RESET' })
    dispatch({ type: 'OPENING_STARTED' })
    runTurn(s.id, [])
  }

  function handleBack() {
    requestId.current += 1 // ignore any reply still on its way
    setScenario(null)
    setDraft('')
    dispatch({ type: 'RESET' })
  }

  async function handleSend() {
    const text = draft.trim()
    if (!text || state.status === 'sending') return
    // The reducer has not applied SEND_STARTED yet, so append the new message by hand.
    const history = [...toHistory(state.messages), { role: 'user', text }]
    dispatch({ type: 'SEND_STARTED', text })
    const ok = await runTurn(scenario.id, history)
    if (ok) setDraft('')
  }

  function handleRetryOpening() {
    dispatch({ type: 'OPENING_STARTED' })
    runTurn(scenario.id, [])
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!scenario) {
    return (
      <div className="conversations-page">
        <h1 className="page-title">Conversations</h1>
        <p className="page-subtitle">
          Pick a situation and chat in German. Nothing is graded; you get gentle corrections.
        </p>
        {scenariosError && <p className="form-error">{scenariosError}</p>}
        <ul className="scenario-list">
          {scenarios.map((s) => (
            <li key={s.id}>
              <button type="button" className="scenario-card" onClick={() => handlePick(s)}>
                {s.title}
              </button>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  const isSending = state.status === 'sending'
  const needsOpening = state.messages.length === 0 && state.status === 'error'

  return (
    <div className="conversations-page conversations-page--chat">
      {topbarSlot &&
        createPortal(
        <div className="chat-header">
        <button type="button" className="btn btn-secondary" onClick={handleBack}>
            Back
        </button>
        <h1 className="chat-title">{scenario.title}</h1>
        </div>,
        topbarSlot,
      )}

      <div className="chat-messages" aria-live="polite">
        {state.messages.map((m) => (
          <ChatMessage key={m.id} message={m} />
        ))}
        {isSending && (
          <div className="chat-typing" role="status">
            <span className="spinner" aria-hidden="true" />
            Typing…
          </div>
        )}
        <div ref={endRef} />
      </div>

      {state.error && <p className="form-error">{state.error}</p>}
      {needsOpening && (
        <button type="button" className="btn btn-secondary" onClick={handleRetryOpening}>
          Try again
        </button>
      )}

      <ChipRow key={state.nextId} chips={state.chips} />

      <div className="chat-input">
        <textarea
          className="chat-textarea"
          rows={2}
          maxLength={MAX_MESSAGE_CHARS}
          placeholder="Write in German… (Enter to send)"
          value={draft}
          disabled={isSending || state.messages.length === 0}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          className="btn btn-primary"
          disabled={isSending || !draft.trim()}
          onClick={handleSend}
        >
          Send
        </button>
      </div>
    </div>
  )
}