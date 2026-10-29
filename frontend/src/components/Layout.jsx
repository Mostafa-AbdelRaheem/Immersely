// src/components/Layout.jsx
import { Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import DueTodayBadge from '../features/session/DueTodayBadge'
import Sidebar from './Sidebar'
import './Layout.css'

export default function Layout() {
  const { user } = useAuth()
  const initial = user?.email ? user.email[0].toUpperCase() : '?'

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <header className="topbar">
          <DueTodayBadge />
          {user && <span className="topbar-user">{user.email}</span>}
          <span className="topbar-avatar" aria-hidden="true">{initial}</span>
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}