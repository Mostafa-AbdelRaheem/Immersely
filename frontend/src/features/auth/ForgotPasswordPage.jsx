import { useState } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../../api/auth'
import './auth.css'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [sentTo, setSentTo] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    const normalized = email.trim().toLowerCase()
    try {
      await forgotPassword(normalized)
      // Same confirmation for every 200: the server never reveals whether the
      // account exists, and neither does this page.
      setSentTo(normalized)
    } catch (err) {
      if (err?.status === 429) {
        setError('Too many attempts. Please wait a minute and try again.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  if (sentTo) {
    return (
      <div className="auth-page">
        <h1>Check your inbox</h1>
        <div className="auth-notice" role="status">
          <p>
            If an account exists for <strong>{sentTo}</strong>, we&apos;ve sent a
            reset link. It expires in 30 minutes.
          </p>
          <p>
            <Link to="/login">Back to log in</Link>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-page">
      <h1>Forgot password</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <p className="form-hint">
            Enter your account email and we&apos;ll send you a reset link.
          </p>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Sending...' : 'Send reset link'}
        </button>
      </form>
      <p className="auth-switch">
        <Link to="/login">Back to log in</Link>
      </p>
    </div>
  )
}