// src/api/scenes.js
import { apiFetch } from './client'

export function requestScene(topic, maxTargets) {
  const body = { topic }
  if (maxTargets !== undefined) {
    body.max_targets = maxTargets
  }
  return apiFetch('/scenes', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}