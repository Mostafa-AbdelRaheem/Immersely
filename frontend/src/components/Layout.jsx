// src/components/Layout.jsx
import { useCallback, useState } from 'react'
import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import DueTodayBadge from '../features/session/DueTodayBadge'
import VerificationBanner from '../features/auth/VerificationBanner'
import Icon from './icons'
import Sidebar from './Sidebar'
import './Layout.css'

export default function Layout() {
  const { user } = useAuth()
  // State, not a ref: pages portal into this element and must re-render once it exists.
  const [topbarSlot, setTopbarSlot] = useState(null)
  // Drawer state lives here because the burger (topbar) and the drawer (Sidebar) are siblings.
  const [menuOpen, setMenuOpen] = useState(false)
  // Stable identity: Sidebar's Escape listener depends on it.
  const closeMenu = useCallback(() => setMenuOpen(false), [])
  const displayName = user?.name || user?.email || ''
  const initial = displayName ? displayName[0].toUpperCase() : '?'

  return (
    <div className="app-shell">
      <Sidebar isOpen={menuOpen} onClose={closeMenu} />
      {menuOpen && <div className="sidebar-backdrop" onClick={closeMenu} aria-hidden="true" />}
      <div className="app-main">
        <header className="topbar">
          <button
            type="button"
            className="topbar-menu"
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
            aria-expanded={menuOpen}
            aria-controls="app-sidebar"
          >
            <Icon name="menu" />
          </button>
          <div className="topbar-slot" ref={setTopbarSlot} />
          <DueTodayBadge />
          {user && (
            <Link to="/profile" className="topbar-profile" aria-label="Account">
              <span className="topbar-user">{displayName}</span>
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
