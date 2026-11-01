// src/features/session/MethodPanel.jsx
import { useState } from 'react'
import { formatTopic } from './formatTopic'
import './MethodPanel.css'

const DEFAULT_FLIP_SIZE = 20

// topic: string | null (null = all topics)
// dueCount: how many sentences are due in that scope
// onStart({ method, direction, limit })
export default function MethodPanel({ topic, dueCount, isStarting, onStart }) {
  const [method, setMethod] = useState('flip')
  const [direction, setDirection] = useState('en-de')
  const [limitText, setLimitText] = useState(String(Math.min(dueCount, DEFAULT_FLIP_SIZE)))

  const limit = Number(limitText)
  const limitValid = Number.isInteger(limit) && limit >= 1 && limit <= dueCount
  const nothingDue = dueCount === 0
  const canStart = !isStarting && !nothingDue && (method !== 'flip' || limitValid)

  function handleStart() {
    if (!canStart) return
    if (method === 'flip') {
      onStart({ method, direction, limit })
    } else {
      onStart({ method })
    }
  }

  return (
    <div className="method-panel">
      <h2 className="method-panel-title">{topic ? formatTopic(topic) : 'All topics'}</h2>
      <p className="method-panel-due">
        {nothingDue ? 'Nothing due right now.' : `${dueCount} due`}
      </p>

      <fieldset className="method-panel-group" disabled={isStarting}>
        <legend>Method</legend>
        <label>
          <input
            type="radio"
            name="method"
            checked={method === 'flip'}
            onChange={() => setMethod('flip')}
          />{' '}
          Flip cards
        </label>
        <label>
          <input
            type="radio"
            name="method"
            checked={method === 'typed'}
            onChange={() => setMethod('typed')}
          />{' '}
          Typed
        </label>
        {topic && (
          <label>
            <input
              type="radio"
              name="method"
              checked={method === 'scene'}
              onChange={() => setMethod('scene')}
            />{' '}
            Scene
          </label>
        )}
      </fieldset>

      {method === 'flip' && (
        <>
          <fieldset className="method-panel-group" disabled={isStarting}>
            <legend>Direction</legend>
            <label>
              <input
                type="radio"
                name="direction"
                checked={direction === 'en-de'}
                onChange={() => setDirection('en-de')}
              />{' '}
              English → German
            </label>
            <label>
              <input
                type="radio"
                name="direction"
                checked={direction === 'de-en'}
                onChange={() => setDirection('de-en')}
              />{' '}
              German → English
            </label>
          </fieldset>

          <div className="method-panel-group">
            <label htmlFor="flip-limit">Number of cards (1–{dueCount})</label>
            <div className="method-panel-limit">
              <input
                id="flip-limit"
                type="number"
                min={1}
                max={dueCount}
                value={limitText}
                disabled={isStarting || nothingDue}
                onChange={(e) => setLimitText(e.target.value)}
              />
              <button
                type="button"
                className="btn btn-secondary"
                disabled={isStarting || nothingDue}
                onClick={() => setLimitText(String(dueCount))}
              >
                All
              </button>
            </div>
            {!nothingDue && !limitValid && (
              <p className="form-error">Enter a whole number from 1 to {dueCount}.</p>
            )}
          </div>
        </>
      )}

      <button type="button" className="btn btn-primary" disabled={!canStart} onClick={handleStart}>
        {isStarting ? 'Preparing…' : 'Start'}
      </button>
    </div>
  )
}