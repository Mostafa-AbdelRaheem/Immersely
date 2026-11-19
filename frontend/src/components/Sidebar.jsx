// src/components/Sidebar.jsx
import { useEffect } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import Icon from './icons'

// Items without `to` have no page yet; they render as disabled "Soon" entries.
const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/sentences', label: 'Cards', icon: 'collections' },
  { to: '/review', label: 'Flashcards', icon: 'flashcards' },
  { to: '/conversations', label: 'Conversations', icon: 'conversation' },
  { to: '/read', label: 'Read', icon: 'reads' },
  { label: 'Settings', icon: 'settings' },
]

// isOpen/onClose only matter on small screens, where the sidebar is a drawer.
// Above the breakpoint the CSS ignores them and the sidebar is always visible.
export default function Sidebar({ isOpen = false, onClose = () => {} }) {
  const { logout } = useAuth()
  const { theme, toggleTheme } = useTheme()

  // Escape closes the drawer. The listener exists only while it is open.
  useEffect(() => {
    if (!isOpen) return undefined
    function handleKeyDown(event) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  return (
    <aside id="app-sidebar" className={`sidebar${isOpen ? ' sidebar--open' : ''}`}>
      <div className="sidebar-header">
        <Link to="/" className="sidebar-brand" onClick={onClose}>
          <span className="sidebar-logo" aria-hidden="true">G</span>
          German SRS
        </Link>
        <button
          type="button"
          className="sidebar-close"
          onClick={onClose}
          aria-label="Close menu"
        >
          <Icon name="close" />
        </button>
      </div>

      <nav className="sidebar-nav" aria-label="Main">
        {NAV_ITEMS.map((item) =>
          item.to ? (
            <NavLink
              key={item.label}
              to={item.to}
              end={item.end}
              onClick={onClose}
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
