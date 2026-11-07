// src/api/conversations.js
import { apiFetch } from './client'

export function listScenarios() {
  return apiFetch('/conversations/scenarios')
}

// history: [{ role: 'user' | 'partner', text }], oldest first, ending with a
// learner message. An empty array asks the partner to open the conversation.
// Resolves to { partner_reply, correction, chips }.
export function sendTurn(scenarioId, history) {
  return apiFetch('/conversations/turn', {
    method: 'POST',
    body: JSON.stringify({ scenario_id: scenarioId, history }),
  })
}