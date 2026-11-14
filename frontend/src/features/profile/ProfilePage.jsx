import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { updateProfile, changePassword } from '../../api/profile'
import {
  PASSWORD_MAX_BYTES,
  mapRegisterError,
  utf8ByteLength,
} from '../auth/registerLogic'
import { mapChangePasswordError } from './profileLogic'
import '../auth/auth.css'
import './profile.css'

const NAME_MAX_LENGTH = 60

function Field({ id, label, error, children }) {
  return (
    <div className={`form-field${error ? ' form-field--invalid' : ''}`}>
      <label htmlFor={id}>{label}</label>
      {children(error ? `${id}-error` : undefined)}
      {error && (
        <p className="form-error" id={`${id}-error`}>
          {error}
        </p>
      )}
    </div>
  )
}

function ProfileSection() {
  const { user, refreshUser } = useAuth()
  const [name, setName] = useState(user.name ?? '')
  const [username, setUsername] = useState(user.username ?? '')
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [saved, setSaved] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError(null)
    setSaved(false)

    const changes = {}
    if (name.trim() !== (user.name ?? '')) changes.name = name
    if (username.trim().toLowerCase() !== (user.username ?? '')) {
      changes.username = username
    }
    if (Object.keys(changes).length === 0) {
      setFieldErrors({})
      return
    }

    setIsSubmitting(true)
    try {
      await updateProfile(changes)
      await refreshUser()
      setFieldErrors({})
      setSaved(true)
    } catch (err) {
      const mapped = mapRegisterError(err)
      setFieldErrors(mapped.fieldErrors)
      setFormError(mapped.formError)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="profile-section">
      <h2>Profile</h2>
      <p className="profile-email">{user.email}</p>
      <form className="profile-form" onSubmit={handleSubmit}>
        <Field id="profile-name" label="Name" error={fieldErrors.name}>
          {(describedBy) => (
            <input
              id="profile-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={NAME_MAX_LENGTH}
              aria-invalid={Boolean(fieldErrors.name)}
              aria-describedby={describedBy}
              required
            />
          )}
        </Field>
        <Field id="profile-username" label="Username" error={fieldErrors.username}>
          {(describedBy) => (
            <input
              id="profile-username"
              type="text"
              autoCapitalize="none"
              spellCheck={false}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              aria-invalid={Boolean(fieldErrors.username)}
              aria-describedby={describedBy}
              required
            />
          )}
        </Field>
        {formError && (
          <p className="form-error" role="alert">
            {formError}
          </p>
        )}
        {saved && (
          <p className="profile-status" role="status">
            Profile saved.
          </p>
        )}
        <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Saving...' : 'Save'}
        </button>
      </form>
    </section>
  )
}

const EMPTY_PW = { current: '', next: '', confirm: '' }

function PasswordSection() {
  const [form, setForm] = useState(EMPTY_PW)
  const [showPassword, setShowPassword] = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [saved, setSaved] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  function setField(key) {
    return (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError(null)
    setSaved(false)

    if (form.next !== form.confirm) {
      setFieldErrors({ confirmPassword: 'The passwords do not match.' })
      return
    }
    setFieldErrors({})

    setIsSubmitting(true)
    try {
      await changePassword(form.current, form.next)
      setForm(EMPTY_PW)
      setSaved(true)
    } catch (err) {
      const mapped = mapChangePasswordError(err)
      setFieldErrors(mapped.fieldErrors)
      setFormError(mapped.formError)
    } finally {
      setIsSubmitting(false)
    }
  }

  const type = showPassword ? 'text' : 'password'
  const byteCount = utf8ByteLength(form.next)
  const overLimit = byteCount > PASSWORD_MAX_BYTES

  return (
    <section className="profile-section">
      <h2>Change password</h2>
      <form className="profile-form" onSubmit={handleSubmit}>
        <Field id="pw-current" label="Current password" error={fieldErrors.currentPassword}>
          {(describedBy) => (
            <input
              id="pw-current"
              type={type}
              autoComplete="current-password"
              value={form.current}
              onChange={setField('current')}
              aria-invalid={Boolean(fieldErrors.currentPassword)}
              aria-describedby={describedBy}
              required
            />
          )}
        </Field>
        <Field id="pw-new" label="New password" error={fieldErrors.newPassword}>
          {(describedBy) => (
            <div className="password-row">
              <input
                id="pw-new"
                type={type}
                autoComplete="new-password"
                value={form.next}
                onChange={setField('next')}
                aria-invalid={Boolean(fieldErrors.newPassword)}
                aria-describedby={describedBy}
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
          )}
        </Field>
        {form.next && (
          <p className={`byte-counter${overLimit ? ' byte-counter--over' : ''}`}>
            {byteCount} / {PASSWORD_MAX_BYTES} bytes
          </p>
        )}
        <Field id="pw-confirm" label="Confirm new password" error={fieldErrors.confirmPassword}>
          {(describedBy) => (
            <input
              id="pw-confirm"
              type={type}
              autoComplete="new-password"
              value={form.confirm}
              onChange={setField('confirm')}
              aria-invalid={Boolean(fieldErrors.confirmPassword)}
              aria-describedby={describedBy}
              required
            />
          )}
        </Field>
        {formError && (
          <p className="form-error" role="alert">
            {formError}
          </p>
        )}
        {saved && (
          <p className="profile-status" role="status">
            Password updated. Your other devices have been signed out.
          </p>
        )}
        <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Updating...' : 'Change password'}
        </button>
      </form>
    </section>
  )
}

function SessionsSection() {
  const { logoutEverywhere } = useAuth()
  const [error, setError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleClick() {
    if (!window.confirm('Sign out of every device, including this one?')) return
    setError(null)
    setIsSubmitting(true)
    try {
      await logoutEverywhere() // success clears the user; ProtectedRoute redirects
    } catch {
      setError('Could not sign you out everywhere. Please try again.')
      setIsSubmitting(false)
    }
  }

  return (
    <section className="profile-section">
      <h2>Sessions</h2>
      <p>Sign out of every device where you are logged in, including this one.</p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button className="btn" type="button" onClick={handleClick} disabled={isSubmitting}>
        {isSubmitting ? 'Signing out...' : 'Log out everywhere'}
      </button>
    </section>
  )
}

export default function ProfilePage() {
  return (
    <div className="profile-page">
      <h1>Account</h1>
      <ProfileSection />
      <PasswordSection />
      <SessionsSection />
    </div>
  )
}