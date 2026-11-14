// src/components/Layout.jsx
import { useState } from 'react'
import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import DueTodayBadge from '../features/session/DueTodayBadge'
import VerificationBanner from '../features/auth/VerificationBanner'
import Sidebar from './Sidebar'
import './Layout.css'

export default function Layout() {
  const { user } = useAuth()
  // State, not a ref: pages portal into this element and must re-render once it exists.
  const [topbarSlot, setTopbarSlot] = useState(null)
  const initial = user?.email ? user.email[0].toUpperCase() : '?'

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <header className="topbar">
          <div className="topbar-slot" ref={setTopbarSlot} />
          <DueTodayBadge />
          {user && (
            <Link to="/profile" className="topbar-profile" aria-label="Account">
              <span className="topbar-user">{user.email}</span>
              <span className="topbar-avatar" aria-hidden="true">{initial}</span>
            </Link>
          )}
        </header>
        <VerificationBanner />
        <main className="app-content">
          <Outlet context={{ topbarSlot }} />
        </main>
      </div>
    </div>
  )
}