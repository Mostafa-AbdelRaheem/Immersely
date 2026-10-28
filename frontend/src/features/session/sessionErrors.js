// src/features/session/sessionErrors.js
// Turns an apiFetch error (which carries .status) into a user-facing message.
export function describeError(err, fallback) {
  if (err?.status === 429) {
    return 'Too many requests. Please wait a moment and try again.'
  }
  return fallback
}