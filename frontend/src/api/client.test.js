// src/api/client.test.js
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, setAccessToken, setUnauthorizedHandler } from './client'

// Just enough of a fetch Response for apiFetch.
const reply = (status, body, { jsonFails = false } = {}) => ({
  ok: status >= 200 && status < 300,
  status,
  json: jsonFails
    ? () => Promise.reject(new SyntaxError('not json'))
    : () => Promise.resolve(body),
})

// apiFetch rejects with an Error; hand it back so tests can inspect it.
async function failure(promise) {
  try {
    await promise
  } catch (err) {
    return err
  }
  throw new Error('expected apiFetch to reject')
}

beforeEach(() => {
  setAccessToken(null)
  setUnauthorizedHandler(null)
  // The refresh path reads document.cookie; don't depend on the test environment.
  vi.stubGlobal('document', { cookie: '' })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('apiFetch error detail', () => {
  it('exposes the server detail object alongside status and message', async () => {
    const detail = { code: 'weak_password', problems: ['breached'] }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(reply(422, { detail })))

    const err = await failure(apiFetch('/auth/register', { method: 'POST' }))

    expect(err.status).toBe(422)
    expect(err.message).toBe('API error: 422')
    expect(err.detail).toEqual(detail)
  })

  it('keeps a plain-string detail as it is', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(reply(400, { detail: 'Bad thing' })),
    )
    const err = await failure(apiFetch('/x'))
    expect(err.detail).toBe('Bad thing')
  })

  it('uses null when the body has no detail', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(reply(500, {})))
    const err = await failure(apiFetch('/x'))
    expect(err.status).toBe(500)
    expect(err.detail).toBeNull()
  })

  it('still throws, with detail null, when the body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(reply(502, null, { jsonFails: true })),
    )
    const err = await failure(apiFetch('/x'))
    expect(err.status).toBe(502)
    expect(err.detail).toBeNull()
  })

  it('exposes the detail of an error that happens on the retry after a refresh', async () => {
    const detail = { code: 'invalid_token' }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(reply(401, {})) // original call
      .mockResolvedValueOnce(reply(200, { access_token: 'NEW' })) // /auth/refresh
      .mockResolvedValueOnce(reply(400, { detail })) // the retry
    vi.stubGlobal('fetch', fetchMock)

    const err = await failure(apiFetch('/auth/reset-password', { method: 'POST' }))

    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(err.status).toBe(400)
    expect(err.detail).toEqual(detail)
  })

  it('reports an expired session with detail null and calls the unauthorized handler', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(reply(401, {})) // original call
        .mockResolvedValueOnce(reply(401, {})), // refresh fails
    )

    const err = await failure(apiFetch('/auth/me'))

    expect(err.status).toBe(401)
    expect(err.detail).toBeNull()
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })

  it('still returns null for a 204', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(reply(204, null)))
    expect(await apiFetch('/sentences/1', { method: 'DELETE' })).toBeNull()
  })
})