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

export function previewImport(file) {
  const body = new FormData()
  body.append('file', file)
  return apiFetch('/sentences/import/preview', { method: 'POST', body })
}

export function confirmImport(rows) {
  return apiFetch('/sentences/import/confirm', {
    method: 'POST',
    body: JSON.stringify({ sentences: rows }),
  })
}

export async function downloadImportTemplate() {
  const response = await apiFetch('/sentences/import/template', { raw: true })
  return response.blob()
}
