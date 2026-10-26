// src/api/review.js
import { apiFetch } from './client'

export function checkAnswer(sentenceId, answer) {
  return apiFetch(`/review/${sentenceId}/check`, {
    method: 'POST',
    body: JSON.stringify({ answer }),
  })
}