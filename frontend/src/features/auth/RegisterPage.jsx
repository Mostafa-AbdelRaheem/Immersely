import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  PASSWORD_MAX_BYTES,
  mapRegisterError,
  utf8ByteLength,
} from './registerLogic'
import './auth.css'

const EMPTY_FORM = {
  name: '',
  username: '',
  email: '',
  confirmEmail: '',
  password: '',
  confirmPassword: '',
}

// Mirrors the 60-character cap on `name` in backend/app/schemas/user.py.
const NAME_MAX_LENGTH = 60

function Field({ id, label, error, hint, children }) {
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined
  return (
    <div className={`form-field${error ? ' form-field--invalid' : ''}`}>
      <label htmlFor={id}>{label}</label>
      {children(describedBy)}
      {hint && !error && (
        <p className="form-hint" id={`${id}-hint`}>
          {hint}
        </p>
      )}
      {error && (
        <p className="form-error" id={`${id}-error`}>
          {error}
        </p>
      )}
    </div>
  )
}

export default function RegisterPage() {
  const [form, setForm] = useState(EMPTY_FORM)
  const [showPassword, setShowPassword] = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [registeredEmail, setRegisteredEmail] = useState(null)

  const { register } = useAuth()

  function setField(e) {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError(null)

    // Client-only checks: saves a round trip (and one of the 5/minute attempts).
    const clientErrors = {}
    if (form.email.trim().toLowerCase() !== form.confirmEmail.trim().toLowerCase()) {
      clientErrors.confirmEmail = 'The email addresses do not match.'
    }
    if (form.password !== form.confirmPassword) {
      clientErrors.confirmPassword = 'The passwords do not match.'
    }
    setFieldErrors(clientErrors)
    if (Object.keys(clientErrors).length > 0) return

    setIsSubmitting(true)
    try {
      await register({
        name: form.name,
        username: form.username,
        email: form.email,
        password: form.password,
      })
      setRegisteredEmail(form.email.trim().toLowerCase())
      setForm(EMPTY_FORM)
    } catch (err) {
      const mapped = mapRegisterError(err)
      setFieldErrors(mapped.fieldErrors)
      setFormError(mapped.formError)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (registeredEmail) {
    return (
      <div className="auth-page">
        <h1>Check your inbox</h1>
        <div className="auth-notice" role="status">
          <p>
            We sent a verification link to <strong>{registeredEmail}</strong>.
            Open it to confirm your address.
          </p>
          <p>
            <Link to="/login">Go to log in</Link>
          </p>
        </div>
      </div>
    )
  }

  const byteCount = utf8ByteLength(form.password)
  const overLimit = byteCount > PASSWORD_MAX_BYTES

  return (
    <div className="auth-page">
      <h1>Register</h1>
      <form className="auth-form" onSubmit={handleSubmit} noValidate={false}>
        <Field id="name" label="Name" error={fieldErrors.name}>
          {(describedBy) => (
            <input
              id="name"
              name="name"
              type="text"
              autoComplete="name"
              value={form.name}
              onChange={setField}
              maxLength={NAME_MAX_LENGTH}
              aria-invalid={Boolean(fieldErrors.name)}
              aria-describedby={describedBy}
              required
            />
          )}
        </Field>

        <Field
          id="username"
          label="Username"
          error={fieldErrors.username}
          hint="Saved in lowercase. Letters, digits and underscores, 3 to 20 characters."
        >
          {(describedBy) => (
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={form.username}
              onChange={setField}
              aria-invalid={Boolean(fieldErrors.username)}
              aria-describedby={describedBy}
              required
            />
          )}
        </Field>

        <Field id="email" label="Email" error={fieldErrors.email}>
          {(describedBy) => (
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={setField}
              aria-invalid={Boolean(fieldErrors.email)}
              aria-describedby={describedBy}
              required
            />
          )}
        </Field>

        <Field id="confirmEmail" label="Confirm email" error={fieldErrors.confirmEmail}>
          {(describedBy) => (
            <input
              id="confirmEmail"
              name="confirmEmail"
              type="email"
              autoComplete="off"
              value={form.confirmEmail}
              onChange={setField}
              aria-invalid={Boolean(fieldErrors.confirmEmail)}
              aria-describedby={describedBy}
              required
            />
          )}
        </Field>

        <Field
          id="password"
          label="Password"
          error={fieldErrors.password}
          hint="At least 8 characters. Common or leaked passwords are rejected, so try a few unrelated words."
        >
          {(describedBy) => (
            <div className="password-row">
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={form.password}
                onChange={setField}
                aria-invalid={Boolean(fieldErrors.password)}
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
        {form.password && (
          <p className={`byte-counter${overLimit ? ' byte-counter--over' : ''}`}>
            {byteCount} / {PASSWORD_MAX_BYTES} bytes
          </p>
        )}

        <Field
          id="confirmPassword"
          label="Confirm password"
          error={fieldErrors.confirmPassword}
        >
          {(describedBy) => (
            <input
              id="confirmPassword"
              name="confirmPassword"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={form.confirmPassword}
              onChange={setField}
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
        <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Registering...' : 'Register'}
        </button>
      </form>
      <p className="auth-switch">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  )
}