import { describe, it, expect } from 'vitest'
import { mapChangePasswordError } from './profileLogic'

const err = (status, detail) => ({ status, detail })

describe('mapChangePasswordError', () => {
  it('maps a wrong current password to its field', () => {
    const r = mapChangePasswordError(err(400, { code: 'current_password_incorrect' }))
    expect(r.fieldErrors.currentPassword).toMatch(/incorrect/i)
    expect(r.formError).toBeNull()
  })

  it('maps same_as_current to the new-password field', () => {
    const r = mapChangePasswordError(err(422, { code: 'same_as_current' }))
    expect(r.fieldErrors.newPassword).toMatch(/differ/i)
  })

  it('maps weak_password problems to the new-password field', () => {
    const r = mapChangePasswordError(
      err(422, { code: 'weak_password', problems: ['too_short'] }),
    )
    expect(r.fieldErrors.newPassword).toMatch(/too short/i)
    expect(r.fieldErrors.password).toBeUndefined()
  })

  it('maps 429 and unknown errors to a form error', () => {
    expect(mapChangePasswordError(err(429, null)).formError).toMatch(/wait a minute/i)
    expect(mapChangePasswordError(err(500, null)).formError).toMatch(/went wrong/i)
  })
})