// src/api/articles.js
import { apiFetch } from './client'

// topic is optional: omit it to list every saved article.
export function listArticles(topic) {
  const query = topic ? `?topic=${encodeURIComponent(topic)}` : ''
  return apiFetch(`/articles${query}`)
}

// Generates and saves a new article (one LLM call, can take a few seconds).
export function createArticle(topic) {
  return apiFetch('/articles', {
    method: 'POST',
    body: JSON.stringify({ topic }),
  })
}

export function getArticle(id) {
  return apiFetch(`/articles/${id}`)
}

// Resolves to null on success (the server answers 204).
export function deleteArticle(id) {
  return apiFetch(`/articles/${id}`, { method: 'DELETE' })
}