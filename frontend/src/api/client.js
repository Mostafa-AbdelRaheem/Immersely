// src/api/client.js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

let currentAccessToken = null
let onUnauthorized = null

export function setAccessToken(token) {
  currentAccessToken = token
}

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

function getCsrfTokenFromCookie() {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : null
}

// Same Error as before (message + status), plus `detail`: the server's
// `detail` field (e.g. { code: 'weak_password', problems: [...] }), or null
// when the body is missing or is not JSON. Never throws while building.
async function buildApiError(response) {
  const err = new Error(`API error: ${response.status}`)
  err.status = response.status
  err.detail = null
  try {
    const body = await response.json()
    err.detail = body?.detail ?? null
  } catch {
    // empty or non-JSON body: keep detail = null
  }
  return err
}

let refreshInFlight = null

export async function refreshAccessToken() {
  if (refreshInFlight) {
    return refreshInFlight
  }

  refreshInFlight = (async () => {
    const csrfToken = getCsrfTokenFromCookie()

    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
    })

    if (!response.ok) {
      return null
    }

    const data = await response.json()
    setAccessToken(data.access_token)
    return data.access_token
  })()

  try {
    return await refreshInFlight
  } finally {
    refreshInFlight = null
  }
}

export async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(currentAccessToken ? { Authorization: `Bearer ${currentAccessToken}` } : {}),
      ...options.headers,
    },
  })

  if (response.status === 401 && path !== '/auth/refresh') {
    const newToken = await refreshAccessToken()

    if (newToken) {
      const retryResponse = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${newToken}`,
          ...options.headers,
        },
      })

      if (!retryResponse.ok) {
        throw await buildApiError(retryResponse)
      }

      if (retryResponse.status === 204) {
        return null
      }
      return retryResponse.json()
    }

    if (onUnauthorized) {
      onUnauthorized()
    }
    const err = new Error('API error: 401 (session expired)')
    err.status = 401
    err.detail = null
    throw err
  }

  if (!response.ok) {
    throw await buildApiError(response)
  }

  if (response.status === 204) {
    return null
  }
  return response.json()
}