import { describe, it, expect } from 'vitest'
import { mapChangePasswordError, mapDeleteAccountError } from './profileLogic'

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

describe('mapDeleteAccountError', () => {
  it('maps a wrong password to the password field', () => {
    const r = mapDeleteAccountError(err(400, { code: 'current_password_incorrect' }))
    expect(r.fieldErrors.password).toMatch(/incorrect/i)
    expect(r.formError).toBeNull()
  })

  it('maps 429 to a form error', () => {
    const r = mapDeleteAccountError(err(429, null))
    expect(r.formError).toMatch(/wait a minute/i)
    expect(r.fieldErrors).toEqual({})
  })

  it('maps unknown errors to a form error', () => {
    const r = mapDeleteAccountError(err(500, null))
    expect(r.formError).toMatch(/went wrong/i)
    expect(r.fieldErrors).toEqual({})
  })

  it('does not throw on a malformed detail', () => {
    expect(mapDeleteAccountError(err(500, 'oops')).formError).toMatch(/went wrong/i)
    expect(mapDeleteAccountError(err(500, ['x'])).formError).toMatch(/went wrong/i)
    expect(mapDeleteAccountError(undefined).formError).toMatch(/went wrong/i)
  })
})
