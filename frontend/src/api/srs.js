// src/api/srs.js
import { apiFetch } from './client'

function withQuery(path, params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null)
  ).toString()
  return query ? `${path}?${query}` : path
}

export function getDueCount(topic) {
  return apiFetch(withQuery('/srs/due/count', { topic }))
}

export function getDueSentences(topic, limit = 50) {
  return apiFetch(withQuery('/srs/due', { topic, limit }))
}

export function gradeSentence(sentenceId, grade) {
  return apiFetch(`/srs/${sentenceId}/grade`, {
    method: 'POST',
    body: JSON.stringify({ grade }),
  })
}