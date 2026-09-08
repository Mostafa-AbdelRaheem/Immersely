import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client.js'
import { useAuth } from '../context/AuthContext'

function Home() {
  const [status, setStatus] = useState('checking...')
  const { user, logout } = useAuth()

  useEffect(() => {
    apiFetch('/health')
      .then((data) => setStatus(data.status))
      .catch(() => setStatus('unreachable'))
  }, [])

  return (
    <div>
      <h1>German SRS — Home</h1>
      <p>Backend status: {status}</p>
      <p>Logged in as: {user?.email}</p>
      <button onClick={logout}>Log out</button>
    </div>
  )
}

export default Home