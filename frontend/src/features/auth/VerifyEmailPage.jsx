import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { verifyEmail } from '../../api/auth'
import { readTokenFromHash } from './tokenFromHash'
import './auth.css'

export default function VerifyEmailPage() {
  const { user, refreshUser } = useAuth()
  // Read once from the URL fragment at first render; never rendered.
  const [token] = useState(() => readTokenFromHash(window.location.hash))
  // No token is known at first render, so it is the starting status
  // rather than something an effect has to set.
  const [status, setStatus] = useState(token ? 'verifying' : 'invalid')
  // Guards the single-use token against StrictMode's double effect run.
  const startedRef = useRef(false)

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true

    // Remove the token from the address bar and history entry.
    window.history.replaceState(null, '', window.location.pathname)

    if (!token) return

    verifyEmail(token)
      .then(() => {
        setStatus('verified')
        refreshUser()
      })
      .catch((err) => {
        setStatus(err?.status === 400 ? 'invalid' : 'error')
      })
  }, [token])

  return (
    <div className="auth-page">
      <h1>Verify email</h1>
      <div className="auth-notice" role="status">
        {status === 'verifying' && <p>Verifying your email...</p>}

        {status === 'verified' && (
          <>
            <p>Your email is verified. Thank you!</p>
            <p>
              {user ? (
                <Link to="/">Continue to the app</Link>
              ) : (
                <Link to="/login">Go to log in</Link>
              )}
            </p>
          </>
        )}

        {status === 'invalid' && (
          <>
            <p>This link is invalid or has expired.</p>
            <p>
              {user ? (
                <Link to="/">Back to the app</Link>
              ) : (
                <Link to="/login">Go to log in</Link>
              )}
            </p>
          </>
        )}

        {status === 'error' && (
          <p>
            We couldn&apos;t verify your email right now. Please open the link from
            your email again in a minute.
          </p>
        )}
      </div>
    </div>
  )
}