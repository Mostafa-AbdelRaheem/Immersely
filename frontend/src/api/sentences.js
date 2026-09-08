// src/api/sentences.js
import { apiFetch } from './client'

export function listSentences() {
  return apiFetch('/sentences')
}

export function getSentence(id) {
  return apiFetch(`/sentences/${id}`)
}

export function createSentence({ de, en }) {
  return apiFetch('/sentences', {
    method: 'POST',
    body: JSON.stringify({ de, en }),
  })
}

export function updateSentence(id, changes) {
  return apiFetch(`/sentences/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}

export function deleteSentence(id) {
  return apiFetch(`/sentences/${id}`, {
    method: 'DELETE',
  })
}