// src/features/profile/profileLogic.js
// Pure helpers for the Profile page: no React, no fetch.
import { mapRegisterError } from '../auth/registerLogic'

// Maps an error from POST /auth/change-password to field messages.
// Fields: currentPassword, newPassword. Anything unknown becomes a formError.
export function mapChangePasswordError(err) {
  const detail = err?.detail
  const code =
    detail && typeof detail === 'object' && !Array.isArray(detail)
      ? detail.code
      : undefined

  if (code === 'current_password_incorrect') {
    return {
      fieldErrors: { currentPassword: 'Your current password is incorrect.' },
      formError: null,
    }
  }
  if (code === 'same_as_current') {
    return {
      fieldErrors: { newPassword: 'The new password must differ from your current one.' },
      formError: null,
    }
  }

  // weak_password, 429 and the generic fallback are already handled there.
  const mapped = mapRegisterError(err)
  if (mapped.fieldErrors.password) {
    return {
      fieldErrors: { newPassword: mapped.fieldErrors.password },
      formError: null,
    }
  }
  return { fieldErrors: {}, formError: mapped.formError }
}