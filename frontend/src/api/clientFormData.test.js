// src/api/clientFormData.test.js
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, setAccessToken, setUnauthorizedHandler } from './client'

const reply = (status, body) => ({
  ok: status >= 200 && status < 300,
  status,
  json: () => Promise.resolve(body),
})

beforeEach(() => {
  setAccessToken(null)
  setUnauthorizedHandler(null)
  vi.stubGlobal('document', { cookie: '' })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const hasContentType = (headers) =>
  Object.keys(headers).some((k) => k.toLowerCase() === 'content-type')

function uploadBody() {
  const form = new FormData()
  form.append('file', new Blob(['x']), 'a.xlsx')
  return form
}

describe('apiFetch Content-Type rule', () => {
  it('sends no Content-Type for a FormData body', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(reply(200, {}))
    vi.stubGlobal('fetch', fetchMock)
    await apiFetch('/up', { method: 'POST', body: uploadBody() })
    expect(hasContentType(fetchMock.mock.calls[0][1].headers)).toBe(false)
  })

  it('still sends application/json for a JSON string body', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(reply(200, {}))
    vi.stubGlobal('fetch', fetchMock)
    await apiFetch('/x', { method: 'POST', body: '{"a":1}' })
    expect(fetchMock.mock.calls[0][1].headers['Content-Type']).toBe('application/json')
  })

  it('still sends application/json when there is no body', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(reply(200, {}))
    vi.stubGlobal('fetch', fetchMock)
    await apiFetch('/x', { method: 'DELETE' })
    expect(fetchMock.mock.calls[0][1].headers['Content-Type']).toBe('application/json')
  })

  it('applies the same rule on the 401 retry (FormData)', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(reply(401, {}))
      .mockResolvedValueOnce(reply(200, { access_token: 'new-token' }))
      .mockResolvedValueOnce(reply(200, { ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    await apiFetch('/up', { method: 'POST', body: uploadBody() })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    const retryOptions = fetchMock.mock.calls[2][1]
    expect(hasContentType(retryOptions.headers)).toBe(false)
    expect(retryOptions.headers.Authorization).toBe('Bearer new-token')
  })

  it('applies the same rule on the 401 retry (JSON)', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(reply(401, {}))
      .mockResolvedValueOnce(reply(200, { access_token: 'new-token' }))
      .mockResolvedValueOnce(reply(200, { ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    await apiFetch('/x', { method: 'POST', body: '{"a":1}' })
    expect(fetchMock.mock.calls[2][1].headers['Content-Type']).toBe('application/json')
  })
})
