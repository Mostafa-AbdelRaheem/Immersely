// src/features/session/formatTopic.js
// 'work_and_career' -> 'Work and career'
export function formatTopic(topic) {
  const spaced = topic.replace(/_/g, ' ').trim()
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}