// src/api/profile.js
// Thin wrappers for the logged-in account endpoints. Errors propagate from
// apiFetch (.status, .detail); the Profile page decides what they mean.
import { apiFetch } from './client'

// Send only the fields being changed: the server rejects an empty object and
// an explicit null. Returns the updated user (name, username, ...).
export function updateProfile({ name, username }) {
  const body = {}
  if (name !== undefined) body.name = name
  if (username !== undefined) body.username = username
  return apiFetch('/auth/me', { method: 'PATCH', body: JSON.stringify(body) })
}

// Passwords are sent exactly as typed: the server normalizes them, and
// trimming here would change what gets verified or hashed. A wrong current
// password is a 400 (code current_password_incorrect), never a 401, so
// apiFetch does not try to refresh the session.
export function changePassword(currentPassword, newPassword) {
  return apiFetch('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
}

// Revokes every session, this device included. The caller must then clear
// its own in-memory token and user, as AuthContext.logout does.
export function logoutAll() {
  return apiFetch('/auth/logout-all', { method: 'POST' })
}