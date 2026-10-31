// src/context/DueCountContext.jsx
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { getDueCount } from '../api/srs'

const DueCountContext = createContext(null)

export function DueCountProvider({ children }) {
  const [count, setCount] = useState(null) // null = not loaded yet
  const [error, setError] = useState(false)
  const latestRequestId = useRef(0)

  const refresh = useCallback(async () => {
    const requestId = ++latestRequestId.current
    try {
      const data = await getDueCount()
      // Ignore this response if a newer refresh has started since.
      if (requestId !== latestRequestId.current) return
      setCount(data.count)
      setError(false)
    } catch {
      if (requestId !== latestRequestId.current) return
      // Keep the previous count; just record that the last refresh failed.
      setError(true)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <DueCountContext.Provider value={{ count, error, refresh }}>
      {children}
    </DueCountContext.Provider>
  )
}

export function useDueCount() {
  const context = useContext(DueCountContext)
  if (!context) {
    throw new Error('useDueCount must be used within a DueCountProvider')
  }
  return context
}