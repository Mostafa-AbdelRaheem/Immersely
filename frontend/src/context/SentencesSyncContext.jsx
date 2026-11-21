// src/context/SentencesSyncContext.jsx
// Lets the global add modal tell the Cards page "the sentence list changed".
// A version number is enough: consumers put it in an effect's dependency list.
import { createContext, useCallback, useContext, useMemo, useState } from 'react'

const SentencesSyncContext = createContext(null)

export function SentencesSyncProvider({ children }) {
  const [sentencesVersion, setSentencesVersion] = useState(0)

  const notifySentencesChanged = useCallback(() => {
    setSentencesVersion((v) => v + 1)
  }, [])

  const value = useMemo(
    () => ({ sentencesVersion, notifySentencesChanged }),
    [sentencesVersion, notifySentencesChanged],
  )

  return (
    <SentencesSyncContext.Provider value={value}>
      {children}
    </SentencesSyncContext.Provider>
  )
}

export function useSentencesSync() {
  const context = useContext(SentencesSyncContext)
  if (!context) {
    throw new Error('useSentencesSync must be used within a SentencesSyncProvider')
  }
  return context
}
