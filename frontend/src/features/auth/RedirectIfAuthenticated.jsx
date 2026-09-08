import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function RedirectIfAuthenticated() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <p>Loading...</p>
  }

  if (user) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}