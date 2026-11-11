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