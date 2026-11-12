// src/features/auth/registerLogic.test.js
import { describe, expect, it } from 'vitest'
import {
  PASSWORD_MAX_BYTES,
  mapRegisterError,
  utf8ByteLength,
} from './registerLogic'

describe('utf8ByteLength', () => {
  it('counts ASCII as one byte per character', () => {
    expect(utf8ByteLength('hello')).toBe(5)
  })

  it('counts an empty string as zero', () => {
    expect(utf8ByteLength('')).toBe(0)
  })

  it('counts a precomposed u-umlaut as two bytes', () => {
    expect(utf8ByteLength('\u00fc')).toBe(2)
  })

  it('counts a decomposed u-umlaut the same as the precomposed form (NFC first)', () => {
    expect(utf8ByteLength('u\u0308')).toBe(2)
  })

  it('counts an emoji as four bytes', () => {
    expect(utf8ByteLength('\u{1F600}')).toBe(4)
  })

  it('exposes the 72-byte limit', () => {
    expect(PASSWORD_MAX_BYTES).toBe(72)
  })
})

describe('mapRegisterError: password', () => {
  it('maps every known weak_password problem to the password field', () => {
    const cases = {
      too_short: 'too short',
      too_long: 'at most',
      same_as_email: 'same as your email',
      breached: 'data leak',
    }
    for (const [problem, fragment] of Object.entries(cases)) {
      const result = mapRegisterError({
        status: 422,
        detail: { code: 'weak_password', problems: [problem] },
      })
      expect(result.fieldErrors.password).toContain(fragment)
      expect(result.formError).toBeNull()
    }
  })

  it('joins several problems into one message', () => {
    const result = mapRegisterError({
      status: 422,
      detail: { code: 'weak_password', problems: ['too_short', 'breached'] },
    })
    expect(result.fieldErrors.password).toContain('too short')
    expect(result.fieldErrors.password).toContain('data leak')
  })

  it('uses a fallback for an unknown problem code', () => {
    const result = mapRegisterError({
      status: 422,
      detail: { code: 'weak_password', problems: ['brand_new_rule'] },
    })
    expect(result.fieldErrors.password).toBe("This password isn't acceptable.")
  })

  it('uses a fallback when problems is missing', () => {
    const result = mapRegisterError({
      status: 422,
      detail: { code: 'weak_password' },
    })
    expect(result.fieldErrors.password).toBe("This password isn't acceptable.")
  })
})

describe('mapRegisterError: username and email', () => {
  it('maps invalid_username problems to the username field', () => {
    const result = mapRegisterError({
      status: 422,
      detail: { code: 'invalid_username', problems: ['invalid_characters'] },
    })
    expect(result.fieldErrors.username).toContain('letters, digits and underscores')
    expect(result.formError).toBeNull()
  })

  it('maps username_taken to the username field', () => {
    const result = mapRegisterError({
      status: 409,
      detail: { code: 'username_taken' },
    })
    expect(result.fieldErrors.username).toContain('taken')
  })

  it('maps email_taken to the email field', () => {
    const result = mapRegisterError({
      status: 409,
      detail: { code: 'email_taken' },
    })
    expect(result.fieldErrors.email).toContain('already exists')
    expect(result.formError).toBeNull()
  })
})

describe('mapRegisterError: fallbacks', () => {
  it('returns the rate-limit message for a 429', () => {
    const result = mapRegisterError({ status: 429, detail: null })
    expect(result.formError).toContain('Too many attempts')
    expect(result.fieldErrors).toEqual({})
  })

  it('returns the generic form error for a null detail', () => {
    const result = mapRegisterError({ status: 500, detail: null })
    expect(result.formError).toBe('Something went wrong. Please try again.')
    expect(result.fieldErrors).toEqual({})
  })

  it('returns the generic form error for an array detail (FastAPI built-in 422)', () => {
    const result = mapRegisterError({
      status: 422,
      detail: [{ loc: ['body', 'name'], msg: 'too long' }],
    })
    expect(result.formError).toBe('Something went wrong. Please try again.')
  })

  it('returns the generic form error for a string detail', () => {
    const result = mapRegisterError({ status: 400, detail: 'nope' })
    expect(result.formError).toBe('Something went wrong. Please try again.')
  })

  it('returns the generic form error for an unknown code', () => {
    const result = mapRegisterError({ status: 400, detail: { code: 'mystery' } })
    expect(result.formError).toBe('Something went wrong. Please try again.')
  })

  it('does not crash on an error with no fields at all', () => {
    expect(mapRegisterError(undefined).formError).toBe(
      'Something went wrong. Please try again.',
    )
  })
})