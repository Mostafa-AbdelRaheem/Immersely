import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client.js'

function Home() {
  const [status, setStatus] = useState('checking...')

  useEffect(() => {
    apiFetch('/health')
      .then((data) => setStatus(data.status))
      .catch(() => setStatus('unreachable'))
  }, [])

  return (
    <div>
      <h1>German SRS — Home</h1>
      <p>Backend status: {status}</p>
    </div>
  )
}

export default Home