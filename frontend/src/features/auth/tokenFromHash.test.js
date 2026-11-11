// src/features/auth/tokenFromHash.test.js
import { describe, expect, it } from 'vitest'
import { readTokenFromHash } from './tokenFromHash'

describe('readTokenFromHash', () => {
  it('reads the token from a hash with a leading #', () => {
    expect(readTokenFromHash('#token=abc123')).toBe('abc123')
  })

  it('also accepts a hash without the leading #', () => {
    expect(readTokenFromHash('token=abc123')).toBe('abc123')
  })

  it('keeps URL-safe base64 characters intact', () => {
    expect(readTokenFromHash('#token=z67y-2eZ_pTG')).toBe('z67y-2eZ_pTG')
  })

  it('ignores other parameters around the token', () => {
    expect(readTokenFromHash('#foo=1&token=abc&bar=2')).toBe('abc')
  })

  it('decodes percent-encoded characters', () => {
    expect(readTokenFromHash('#token=a%2Bb')).toBe('a+b')
  })

  it('returns null for an empty string', () => {
    expect(readTokenFromHash('')).toBeNull()
  })

  it('returns null for a bare #', () => {
    expect(readTokenFromHash('#')).toBeNull()
  })

  it('returns null when the token value is empty', () => {
    expect(readTokenFromHash('#token=')).toBeNull()
  })

  it('returns null when the token is only whitespace', () => {
    expect(readTokenFromHash('#token=%20%20')).toBeNull()
  })

  it('returns null when there is no token key', () => {
    expect(readTokenFromHash('#other=abc')).toBeNull()
  })

  it('returns null for non-string input', () => {
    expect(readTokenFromHash(undefined)).toBeNull()
    expect(readTokenFromHash(null)).toBeNull()
    expect(readTokenFromHash(123)).toBeNull()
  })
})