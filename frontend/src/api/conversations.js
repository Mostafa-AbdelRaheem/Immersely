// src/api/conversations.js
import { apiFetch } from './client'

export function listScenarios() {
  return apiFetch('/conversations/scenarios')
}

// history: [{ role: 'user' | 'partner', text }], oldest first, ending with a
// learner message. An empty array asks the partner to open the conversation.
// level: 'A1' to 'C2'. Leave it undefined and the server uses its default.
// Resolves to { partner_reply, correction, chips }.
export function sendTurn(scenarioId, history, level) {
  return apiFetch('/conversations/turn', {
    method: 'POST',
    body: JSON.stringify({ scenario_id: scenarioId, history, level }),
  })
}