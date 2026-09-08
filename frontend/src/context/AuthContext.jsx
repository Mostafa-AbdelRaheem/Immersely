import { createContext, useContext, useEffect, useState } from 'react'
import { apiFetch, refreshAccessToken, setAccessToken, setUnauthorizedHandler } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null)
      setAccessToken(null)
    })
  }, [])

  useEffect(() => {
    async function tryRestoreSession() {
      try {
        const token = await refreshAccessToken()

        if (!token) {
          setIsLoading(false)
          return
        }

        const me = await apiFetch('/auth/me')
        setUser(me)
      } catch {
        // no valid session, that's fine
      } finally {
        setIsLoading(false)
      }
    }

    tryRestoreSession()
  }, [])

  async function login(email, password) {
    const data = await apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })

    setAccessToken(data.access_token)

    const me = await apiFetch('/auth/me')
    setUser(me)
  }

  async function register(email, password) {
    await apiFetch('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async function logout() {
    await apiFetch('/auth/logout', { method: 'POST' })
    setAccessToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}