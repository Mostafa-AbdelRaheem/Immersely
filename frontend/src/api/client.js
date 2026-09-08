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
        throw new Error(`API error: ${retryResponse.status}`)
      }

      return retryResponse.json()
    }

    if (onUnauthorized) {
      onUnauthorized()
    }
    throw new Error('API error: 401 (session expired)')
  }

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}