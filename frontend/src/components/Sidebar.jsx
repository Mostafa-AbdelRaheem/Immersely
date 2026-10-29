// src/components/Sidebar.jsx
import { NavLink, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import Icon from './icons'

// Items without `to` have no page yet (stubs come in a later step).
const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/sentences', label: 'Collections', icon: 'collections' },
  { to: '/review', label: 'Flashcards', icon: 'flashcards' },
  { to: '/stats', label: 'Stats', icon: 'stats' },
  { label: 'Conversation', icon: 'conversation' },
  { label: 'Reads', icon: 'reads' },
  { label: 'Settings', icon: 'settings' },
]

export default function Sidebar() {
  const { logout } = useAuth()
  const { theme, toggleTheme } = useTheme()

  return (
    <aside className="sidebar">
      <Link to="/" className="sidebar-brand">
        <span className="sidebar-logo" aria-hidden="true">G</span>
        German SRS
      </Link>

      <nav className="sidebar-nav" aria-label="Main">
        {NAV_ITEMS.map((item) =>
          item.to ? (
            <NavLink
              key={item.label}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-item${isActive ? ' nav-item--active' : ''}`}
            >
              <Icon name={item.icon} />
              {item.label}
            </NavLink>
          ) : (
            <span key={item.label} className="nav-item nav-item--disabled" aria-disabled="true">
              <Icon name={item.icon} />
              {item.label}
              <span className="nav-soon">Soon</span>
            </span>
          ),
        )}
      </nav>

      <div className="sidebar-spacer" />

      <div className="sidebar-footer">
        <button type="button" className="nav-item" onClick={toggleTheme}>
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
        <button type="button" className="nav-item" onClick={logout}>
          <Icon name="logout" />
          Logout
        </button>
      </div>
    </aside>
  )
}