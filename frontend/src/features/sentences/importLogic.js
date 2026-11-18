// src/features/sentences/importLogic.js
// Pure helpers for the bulk import modal: no React, no fetch.

// Mirrors BLOCKING_ISSUES in the backend's bulk_import_logic.py.
const BLOCKING = new Set(['empty_de', 'empty_en', 'too_long_de', 'too_long_en'])

// Mirrors the backend's normalize_for_dedupe: NFC, collapse whitespace, trim,
// casefold. JS has no casefold(), so lowercase + sharp-s -> "ss" (toLowerCase
// turns the capital sharp s into "ß" first). Not a full casefold port, but it
// covers German input.
export function normalizeForDedupe(text) {
  return text
    .normalize('NFC')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
    .replace(/ß/g, 'ss')
}

// Python's len() counts code points; JS .length counts UTF-16 units.
function codePointLength(text) {
  return [...text].length
}

// Recomputes the issues the user can change by editing: empty_*, too_long_*
// and duplicate_in_file (which depends on the other rows, so it takes them
// all). duplicate_existing needs the database, so it is kept as received.
// Returns new row objects; the input is never mutated.
export function recheckRows(rows, maxLen) {
  const seen = new Set()
  return rows.map((row) => {
    const de = row.de.trim()
    const en = row.en.trim()
    const issues = []
    if (!de) issues.push('empty_de')
    else if (codePointLength(de) > maxLen) issues.push('too_long_de')
    if (!en) issues.push('empty_en')
    else if (codePointLength(en) > maxLen) issues.push('too_long_en')
    if (de) {
      const key = normalizeForDedupe(de)
      if (seen.has(key)) issues.push('duplicate_in_file')
      else seen.add(key)
    }
    if ((row.issues ?? []).includes('duplicate_existing')) {
      issues.push('duplicate_existing')
    }
    return {
      ...row,
      issues,
      has_blocking_issue: issues.some((code) => BLOCKING.has(code)),
    }
  })
}

// Same idiom as profileLogic.js: a 422 schema failure has a list as its
// detail, our import codes are objects.
function codeOf(err) {
  const detail = err?.detail
  return detail && typeof detail === 'object' && !Array.isArray(detail)
    ? detail.code
    : undefined
}

const RATE_LIMITED = "You've hit the import limit. Wait a minute and try again."

// Errors from POST /sentences/import/preview. 401 is handled by apiFetch.
export function describeImportError(err) {
  const code = codeOf(err)
  const detail = err?.detail
  if (err?.status === 429) return RATE_LIMITED
  if (code === 'unreadable') {
    return "We couldn't read that file. Make sure it is a valid .xlsx spreadsheet."
  }
  if (code === 'too_large') return 'That file is too large. Try a smaller file.'
  if (code === 'sheet_too_long') {
    return 'That sheet is too long to read. Split it into smaller files.'
  }
  if (code === 'too_many_rows') {
    return `That file has ${detail.count} rows, but the limit is ${detail.limit}. Split it into smaller files.`
  }
  if (code === 'missing_columns') {
    return `The first row needs columns named "de" and "en". Missing: ${detail.missing.join(', ')}.`
  }
  return 'Something went wrong reading that file. Please try again.'
}

// Errors from POST /sentences/import/confirm. The save is one transaction, so
// a failure means nothing was saved. 401 is handled by apiFetch.
export function describeConfirmError(err) {
  if (err?.status === 429) return RATE_LIMITED
  if (err?.status === 422) {
    return 'The server rejected some rows, so nothing was saved. Check the tags and text lengths and try again.'
  }
  return 'Something went wrong, so nothing was saved. You can safely try again.'
}
