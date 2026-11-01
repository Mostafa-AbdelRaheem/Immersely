// src/api/review.js
import { apiFetch } from './client'

export function checkAnswer(sentenceId, answer) {
  return apiFetch(`/review/${sentenceId}/check`, {
    method: 'POST',
    body: JSON.stringify({ answer }),
  })
}

// method omitted: a topic means scene mode, no topic means typed (all topics).
// method 'typed' with a topic: typed isolated sentences for that topic.
// method 'scene' requires a topic.
export function startSession(topic, maxTargets, method) {
  const body = {}
  if (topic) {
    body.topic = topic
  }
  if (maxTargets !== undefined) {
    body.max_targets = maxTargets
  }
  if (method) {
    body.method = method
  }
  return apiFetch('/review/session/start', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// Flip-card session: `limit` is how many cards the user wants (the server
// caps it). topic null/undefined = all topics. The response carries German.
export function startFlipSession(topic, limit) {
  const body = { limit }
  if (topic) {
    body.topic = topic
  }
  return apiFetch('/review/flip/start', {
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

// Self-graded flip card: only the grade. The server derives the tier and
// logs the event with mode 'flip'.
export function gradeFlip(sentenceId, grade) {
  return apiFetch(`/review/${sentenceId}/flip-grade`, {
    method: 'POST',
    body: JSON.stringify({ grade }),
  })
}