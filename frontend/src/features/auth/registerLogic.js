// src/features/auth/registerLogic.js
// Pure helpers for the Register page: no React, no fetch, so Vitest can
// cover them directly.

// Mirrors the backend's Settings.password_max_bytes (app/core/config.py, capped
// at 72 because bcrypt ignores everything past 72 bytes). Duplicated on purpose:
// there is no public-config endpoint. If that Setting ever changes, update this.
export const PASSWORD_MAX_BYTES = 72

// Bytes, not characters: "ü" is 2 bytes and an emoji is 4. The server NFC-normalizes
// before measuring, so we do too, otherwise a decomposed "ü" would be over-counted.
export function utf8ByteLength(str) {
  return new TextEncoder().encode(str.normalize('NFC')).length
}

const GENERIC_ERROR = 'Something went wrong. Please try again.'

const PASSWORD_MESSAGES = {
  too_short: 'This password is too short.',
  too_long: `Password must be at most ${PASSWORD_MAX_BYTES} bytes (accented letters and emoji use more than one each).`,
  same_as_email: "Password can't be the same as your email.",
  breached:
  'This password has appeared in a public data leak, so attackers already try it. Pick a longer, less guessable one, such as three or four unrelated words.',
}
const PASSWORD_FALLBACK = "This password isn't acceptable."

const USERNAME_MESSAGES = {
  too_short: 'This username is too short.',
  too_long: 'This username is too long.',
  invalid_characters: 'Use only letters, digits and underscores.',
}
const USERNAME_FALLBACK = "This username isn't acceptable."

// Unknown codes get a fallback instead of being dropped, so a newly added
// server-side problem code never produces a silent, message-less failure.
function joinProblems(problems, messages, fallback) {
  const list = Array.isArray(problems) && problems.length > 0 ? problems : [null]
  const texts = list.map((p) => messages[p] ?? fallback)
  return [...new Set(texts)].join(' ')
}

// err is what apiFetch throws: { status, detail, message }. detail is an object
// ({ code, problems }) for our own errors, an array for FastAPI's built-in 422s,
// a string for some others, or null.
export function mapRegisterError(err) {
  const fieldErrors = {}
  const detail = err?.detail
  const isObject = detail && typeof detail === 'object' && !Array.isArray(detail)

  switch (isObject ? detail.code : undefined) {
    case 'weak_password':
      fieldErrors.password = joinProblems(detail.problems, PASSWORD_MESSAGES, PASSWORD_FALLBACK)
      return { fieldErrors, formError: null }
    case 'invalid_username':
      fieldErrors.username = joinProblems(detail.problems, USERNAME_MESSAGES, USERNAME_FALLBACK)
      return { fieldErrors, formError: null }
    case 'email_taken':
      fieldErrors.email = 'An account with this email already exists.'
      return { fieldErrors, formError: null }
    case 'username_taken':
      fieldErrors.username = 'This username is taken. Please choose another.'
      return { fieldErrors, formError: null }
    default:
      break
  }

  if (err?.status === 429) {
    return {
      fieldErrors,
      formError: 'Too many attempts. Please wait a minute and try again.',
    }
  }

  return { fieldErrors, formError: GENERIC_ERROR }
}