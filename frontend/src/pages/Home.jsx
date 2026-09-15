import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client.js'
import { useAuth } from '../context/AuthContext'
import DueTodayBadge from '../features/session/DueTodayBadge'

function Home() {
  const [status, setStatus] = useState('checking...')
  const { user } = useAuth()

  useEffect(() => {
    apiFetch('/health')
      .then((data) => setStatus(data.status))
      .catch(() => setStatus('unreachable'))
  }, [])

  return (
    <div className="home-page">
      <div className="home-hero">
        <h1>Welcome back{user?.email ? `, ${user.email}` : ''}</h1>
        <p className="home-subtitle">Here's where things stand today.</p>
      </div>

      <div className="home-cards">
        <div className="home-card">
          <span className="home-card-label">Backend status</span>
          <span className={`status-pill status-pill--${status === 'ok' ? 'ok' : 'down'}`}>
            {status}
          </span>
        </div>

        <div className="home-card">
          <span className="home-card-label">Review queue</span>
          <DueTodayBadge />
        </div>
      </div>
    </div>
  )
}

export default Home