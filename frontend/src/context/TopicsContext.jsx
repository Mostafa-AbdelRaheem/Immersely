// src/context/TopicsContext.jsx
import { createContext, useContext, useEffect, useState } from 'react'
import { listTopics } from '../api/topics'

const TopicsContext = createContext(null)

export function TopicsProvider({ children }) {
  const [topics, setTopics] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function fetchTopics() {
      try {
        const data = await listTopics()
        setTopics(data)
      } catch {
        // topics failed to load; filter/editor will just show an empty list
      } finally {
        setIsLoading(false)
      }
    }

    fetchTopics()
  }, [])

  return (
    <TopicsContext.Provider value={{ topics, isLoading }}>
      {children}
    </TopicsContext.Provider>
  )
}

export function useTopics() {
  const context = useContext(TopicsContext)
  if (!context) {
    throw new Error('useTopics must be used within a TopicsProvider')
  }
  return context
}