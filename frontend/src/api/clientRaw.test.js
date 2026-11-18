// src/api/clientRaw.test.js
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, setAccessToken, setUnauthorizedHandler } from './client'

const reply = (status, body) => ({
  ok: status >= 200 && status < 300,
  status,
  json: vi.fn(() => Promise.resolve(body)),
  blob: vi.fn(() => Promise.resolve(new Blob(['x']))),
})

beforeEach(() => {
  setAccessToken(null)
  setUnauthorizedHandler(null)
  vi.stubGlobal('document', { cookie: '' })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('apiFetch raw option', () => {
  it('returns the Response itself and never parses JSON', async () => {
    const res = reply(200, {})
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(res))
    const out = await apiFetch('/file', { raw: true })
    expect(out).toBe(res)
    expect(res.json).not.toHaveBeenCalled()
  })

  it('does not forward raw to fetch', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(reply(200, {}))
    vi.stubGlobal('fetch', fetchMock)
    await apiFetch('/file', { raw: true })
    expect('raw' in fetchMock.mock.calls[0][1]).toBe(false)
  })

  it('still throws a detailed error on a non-2xx response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(reply(413, { detail: { code: 'too_large' } })),
    )
    await expect(apiFetch('/file', { raw: true })).rejects.toMatchObject({
      status: 413,
      detail: { code: 'too_large' },
    })
  })

  it('returns the retry Response after a 401 refresh', async () => {
    const retry = reply(200, {})
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(reply(401, {}))
        .mockResolvedValueOnce(reply(200, { access_token: 'new-token' }))
        .mockResolvedValueOnce(retry),
    )
    expect(await apiFetch('/file', { raw: true })).toBe(retry)
  })
})
