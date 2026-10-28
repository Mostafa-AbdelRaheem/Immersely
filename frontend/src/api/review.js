// src/api/review.js
import { apiFetch } from './client'

export function checkAnswer(sentenceId, answer) {
  return apiFetch(`/review/${sentenceId}/check`, {
    method: 'POST',
    body: JSON.stringify({ answer }),
  })
}

// topic = a topic string -> scene mode; null/undefined -> isolated mode (all topics)
export function startSession(topic, maxTargets) {
  const body = {}
  if (topic) {
    body.topic = topic
  }
  if (maxTargets !== undefined) {
    body.max_targets = maxTargets
  }
  return apiFetch('/review/session/start', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// Sent on Continue: the FINAL grade (suggested or overridden) plus the
// /check result. Only the fields the backend accepts are sent.
export function gradeReview(
  sentenceId,
  { grade, tier, userInput, correctedInput, rulePracticed, sceneId },
) {
  return apiFetch(`/review/${sentenceId}/grade`, {
    method: 'POST',
    body: JSON.stringify({
      grade,
      tier,
      user_input: userInput,
      corrected_input: correctedInput ?? null,
      rule_practiced: rulePracticed ?? null,
      scene_id: sceneId ?? null,
    }),
  })
}