// src/api/auth.js
// Thin wrappers for the logged-out account endpoints. login/register still
// live in AuthContext; only the newer calls are here. Errors propagate from
// apiFetch (.status, .detail) and the calling page decides what they mean.
import { apiFetch } from './client'

export function verifyEmail(token) {
  return apiFetch('/auth/verify-email', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}

// The server answers 200 with the same body whether or not the email has an
// account, so callers must not treat the response as proof either way.
export function forgotPassword(email) {
  return apiFetch('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

// The server's field is `new_password`. The password is sent exactly as typed:
// the server normalizes it, and trimming here would change what gets hashed.
export function resetPassword(token, password) {
  return apiFetch('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, new_password: password }),
  })
}

// Needs a logged-in user (bearer token). 409 already_verified, 429 and 502
// propagate to the caller.
export function resendVerification() {
  return apiFetch('/auth/resend-verification', { method: 'POST' })
}