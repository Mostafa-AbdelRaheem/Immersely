// src/components/Navbar.jsx
import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import DueTodayBadge from '../features/session/DueTodayBadge'

export default function Navbar() {
  const { user, logout } = useAuth()

  return (
    <nav className="navbar">
      <div className="navbar-left">
        <NavLink to="/" end className="navbar-brand">
          German SRS
        </NavLink>
        <NavLink
          to="/"
          end
          className={({ isActive }) => `navbar-link${isActive ? ' navbar-link--active' : ''}`}
        >
          Home
        </NavLink>
        <NavLink
          to="/sentences"
          className={({ isActive }) => `navbar-link${isActive ? ' navbar-link--active' : ''}`}
        >
          My Sentences
        </NavLink>
      </div>

      <div className="navbar-right">
        <DueTodayBadge />
        {user && <span className="navbar-user">{user.email}</span>}
        <button type="button" className="btn btn-secondary" onClick={logout}>
          Log out
        </button>
      </div>
    </nav>
  )
}