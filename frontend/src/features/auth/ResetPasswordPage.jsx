import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { resetPassword } from '../../api/auth'
import {
  PASSWORD_MAX_BYTES,
  mapRegisterError,
  utf8ByteLength,
} from './registerLogic'
import { readTokenFromHash } from './tokenFromHash'
import './auth.css'

export default function ResetPasswordPage() {
  // Read once from the URL fragment at first render; never rendered.
  const [token] = useState(() => readTokenFromHash(window.location.hash))
  const [status, setStatus] = useState(token ? 'form' : 'invalid')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    // Remove the token from the address bar and history entry.
    window.history.replaceState(null, '', window.location.pathname)
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError(null)

    if (password !== confirmPassword) {
      setFieldErrors({ confirmPassword: 'The passwords do not match.' })
      return
    }
    setFieldErrors({})

    setIsSubmitting(true)
    try {
      await resetPassword(token, password)
      setPassword('')
      setConfirmPassword('')
      setStatus('done')
    } catch (err) {
      if (err?.status === 400 && err?.detail?.code === 'invalid_token') {
        setStatus('invalid')
      } else {
        const mapped = mapRegisterError(err)
        setFieldErrors(mapped.fieldErrors)
        setFormError(mapped.formError)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  if (status === 'done') {
    return (
      <div className="auth-page">
        <h1>Password updated</h1>
        <div className="auth-notice" role="status">
          <p>Your password was changed and your other sessions were logged out.</p>
          <p>
            <Link to="/login">Go to log in</Link>
          </p>
        </div>
      </div>
    )
  }

  if (status === 'invalid') {
    return (
      <div className="auth-page">
        <h1>Reset password</h1>
        <div className="auth-notice" role="status">
          <p>This link is invalid or has expired.</p>
          <p>
            <Link to="/forgot-password">Request a new link</Link>
          </p>
        </div>
      </div>
    )
  }

  const byteCount = utf8ByteLength(password)
  const overLimit = byteCount > PASSWORD_MAX_BYTES

  return (
    <div className="auth-page">
      <h1>Reset password</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <div className={`form-field${fieldErrors.password ? ' form-field--invalid' : ''}`}>
          <label htmlFor="password">New password</label>
          <div className="password-row">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={Boolean(fieldErrors.password)}
              aria-describedby={fieldErrors.password ? 'password-error' : undefined}
              required
            />
            <button
              type="button"
              className="password-toggle"
              aria-pressed={showPassword}
              onClick={() => setShowPassword((v) => !v)}
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>
          {fieldErrors.password && (
            <p className="form-error" id="password-error">
              {fieldErrors.password}
            </p>
          )}
        </div>
        {password && (
          <p className={`byte-counter${overLimit ? ' byte-counter--over' : ''}`}>
            {byteCount} / {PASSWORD_MAX_BYTES} bytes
          </p>
        )}

        <div
          className={`form-field${fieldErrors.confirmPassword ? ' form-field--invalid' : ''}`}
        >
          <label htmlFor="confirmPassword">Confirm new password</label>
          <input
            id="confirmPassword"
            type={showPassword ? 'text' : 'password'}
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            aria-invalid={Boolean(fieldErrors.confirmPassword)}
            aria-describedby={
              fieldErrors.confirmPassword ? 'confirmPassword-error' : undefined
            }
            required
          />
          {fieldErrors.confirmPassword && (
            <p className="form-error" id="confirmPassword-error">
              {fieldErrors.confirmPassword}
            </p>
          )}
        </div>

        {formError && (
          <p className="form-error" role="alert">
            {formError}
          </p>
        )}
        <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Updating...' : 'Update password'}
        </button>
      </form>
    </div>
  )
}