// src/api/sentences.test.js
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { setAccessToken, setUnauthorizedHandler } from './client'
import { confirmImport, downloadImportTemplate, previewImport } from './sentences'

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

describe('previewImport', () => {
  it('POSTs the file as multipart FormData under the field name "file"', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(reply(200, {}))
    vi.stubGlobal('fetch', fetchMock)
    const file = new File(['x'], 'sentences.xlsx')
    await previewImport(file)
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url).endsWith('/sentences/import/preview')).toBe(true)
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(FormData)
    expect(init.body.get('file')).toBe(file)
  })

  it('returns the parsed JSON from the server', async () => {
    const payload = { rows: [], total: 0 }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(reply(200, payload)))
    const out = await previewImport(new File(['x'], 'a.xlsx'))
    expect(out).toEqual(payload)
  })
})

describe('confirmImport', () => {
  it('POSTs a JSON body shaped { sentences: rows }', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(reply(201, []))
    vi.stubGlobal('fetch', fetchMock)
    const rows = [{ de: 'Hallo', en: 'Hello', topics: [], grammar_tag: null }]
    await confirmImport(rows)
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url).endsWith('/sentences/import/confirm')).toBe(true)
    expect(init.method).toBe('POST')
    expect(typeof init.body).toBe('string')
    expect(JSON.parse(init.body)).toEqual({ sentences: rows })
  })

  it('returns the parsed list of saved sentences', async () => {
    const saved = [{ id: 'a' }, { id: 'b' }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(reply(201, saved)))
    expect(await confirmImport([])).toEqual(saved)
  })
})

describe('downloadImportTemplate', () => {
  it('GETs the template URL', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(reply(200, {}))
    vi.stubGlobal('fetch', fetchMock)
    await downloadImportTemplate()
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url).endsWith('/sentences/import/template')).toBe(true)
    expect(init.method ?? 'GET').toBe('GET')
  })

  it('returns the Blob from the response without parsing JSON', async () => {
    const res = reply(200, {})
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(res))
    const out = await downloadImportTemplate()
    expect(out).toBeInstanceOf(Blob)
    expect(res.blob).toHaveBeenCalledTimes(1)
    expect(res.json).not.toHaveBeenCalled()
  })
})
