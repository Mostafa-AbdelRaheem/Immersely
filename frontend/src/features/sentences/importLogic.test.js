import { describe, it, expect } from 'vitest'
import {
  describeConfirmError,
  describeImportError,
  normalizeForDedupe,
  recheckRows,
} from './importLogic'

const err = (status, detail) => ({ status, detail })
const row = (de, en, issues = []) => ({ row_number: 2, de, en, issues })

describe('normalizeForDedupe', () => {
  it('treats sharp s, ss and the capital sharp s as the same', () => {
    const a = normalizeForDedupe('Straße')
    expect(normalizeForDedupe('STRASSE')).toBe(a)
    expect(normalizeForDedupe('Stra\u1E9EE')).toBe(a)
  })

  it('treats NFC and NFD umlauts as the same', () => {
    expect(normalizeForDedupe('a\u0308')).toBe(normalizeForDedupe('\u00E4'))
  })

  it('collapses tabs and repeated spaces and trims', () => {
    expect(normalizeForDedupe('  Ich \t  bin   da ')).toBe('ich bin da')
  })

  it('keeps punctuation', () => {
    expect(normalizeForDedupe('Hallo!')).not.toBe(normalizeForDedupe('Hallo'))
  })
})

describe('recheckRows', () => {
  it('flags empty de and en as blocking', () => {
    const [a, b] = recheckRows([row('', 'x'), row('y', '   ')], 2000)
    expect(a.issues).toEqual(['empty_de'])
    expect(a.has_blocking_issue).toBe(true)
    expect(b.issues).toEqual(['empty_en'])
    expect(b.has_blocking_issue).toBe(true)
  })

  it('clears a stale blocking issue once the text is fixed', () => {
    const [a] = recheckRows([row('Hallo', 'Hi', ['empty_en'])], 2000)
    expect(a.issues).toEqual([])
    expect(a.has_blocking_issue).toBe(false)
  })

  it('does not trust the has_blocking_issue the server sent', () => {
    const wasBlocked = { ...row('Hallo', 'Hi', ['empty_en']), has_blocking_issue: true }
    const wasFine = { ...row('Hallo', ''), has_blocking_issue: false }
    const [fixed, broken] = recheckRows([wasBlocked, wasFine], 2000)
    expect(fixed.has_blocking_issue).toBe(false)
    expect(broken.has_blocking_issue).toBe(true)
  })

  it('allows exactly maxLen and flags one more', () => {
    const [ok, long] = recheckRows([row('a'.repeat(5), 'x'), row('b'.repeat(6), 'y')], 5)
    expect(ok.issues).toEqual([])
    expect(long.issues).toEqual(['too_long_de'])
  })

  it('counts length in code points, not UTF-16 units', () => {
    const emoji = '\u{1F600}'.repeat(3)
    const [a] = recheckRows([row('x', emoji)], 3)
    expect(a.issues).toEqual([])
  })

  it('flags later copies as duplicate_in_file but not the first', () => {
    const [a, b] = recheckRows([row('Straße', 'a'), row('STRASSE', 'b')], 2000)
    expect(a.issues).toEqual([])
    expect(b.issues).toEqual(['duplicate_in_file'])
    expect(b.has_blocking_issue).toBe(false)
  })

  it('makes the second copy clean when the first is gone', () => {
    const [b] = recheckRows([row('STRASSE', 'b')], 2000)
    expect(b.issues).toEqual([])
  })

  it('carries duplicate_existing through unchanged', () => {
    const [a] = recheckRows([row('Hallo', 'Hi', ['duplicate_existing'])], 2000)
    expect(a.issues).toEqual(['duplicate_existing'])
    expect(a.has_blocking_issue).toBe(false)
  })

  it('keeps the server issue order', () => {
    const [, b] = recheckRows(
      [row('Hallo', 'Hi'), row('hallo', '', ['duplicate_existing'])],
      2000,
    )
    expect(b.issues).toEqual(['empty_en', 'duplicate_in_file', 'duplicate_existing'])
  })

  it('does not mutate its input', () => {
    const input = [row('Hallo', 'Hi', ['empty_en'])]
    const copy = JSON.parse(JSON.stringify(input))
    recheckRows(input, 2000)
    expect(input).toEqual(copy)
  })
})

describe('describeImportError', () => {
  it('maps each known code to a message', () => {
    expect(describeImportError(err(400, { code: 'unreadable' }))).toMatch(/couldn't read/i)
    expect(describeImportError(err(413, { code: 'too_large' }))).toMatch(/too large/i)
    expect(describeImportError(err(413, { code: 'sheet_too_long' }))).toMatch(/too long/i)
  })

  it('includes the counts for too_many_rows', () => {
    const msg = describeImportError(
      err(413, { code: 'too_many_rows', limit: 100, count: 150 }),
    )
    expect(msg).toMatch(/150/)
    expect(msg).toMatch(/100/)
  })

  it('lists the missing columns', () => {
    const msg = describeImportError(err(422, { code: 'missing_columns', missing: ['de', 'en'] }))
    expect(msg).toMatch(/de, en/)
  })

  it('maps 429 by status alone and falls back for unknown shapes', () => {
    expect(describeImportError(err(429, null))).toMatch(/wait a minute/i)
    expect(describeImportError(err(422, [{ msg: 'x' }]))).toMatch(/went wrong/i)
    expect(describeImportError(undefined)).toMatch(/went wrong/i)
  })
})

describe('describeConfirmError', () => {
  it('says nothing was saved for 422 and generic failures, and maps 429', () => {
    expect(describeConfirmError(err(422, []))).toMatch(/nothing was saved/i)
    expect(describeConfirmError(err(500, null))).toMatch(/nothing was saved/i)
    expect(describeConfirmError(err(429, null))).toMatch(/wait a minute/i)
  })
})
