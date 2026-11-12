import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { resendVerification } from '../../api/auth'
import './verification-banner.css'

export default function VerificationBanner() {
  const { user, refreshUser } = useAuth()
  const [isSending, setIsSending] = useState(false)
  const [message, setMessage] = useState(null)

  if (!user || user.email_verified_at) return null

  async function handleResend() {
    setIsSending(true)
    setMessage(null)
    try {
      await resendVerification()
      setMessage('Verification email sent.')
    } catch (err) {
      if (err?.status === 409 && err?.detail?.code === 'already_verified') {
        // The server says this account is verified: our copy of user is stale.
        await refreshUser()
      } else if (err?.status === 429) {
        setMessage('Too many requests. Please wait a minute.')
      } else {
        setMessage("Couldn't send right now. Please try again later.")
      }
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div className="verification-banner">
      <span>
        Please verify your email. We sent a link to <strong>{user.email}</strong>.
      </span>
      <button
        type="button"
        className="btn verification-banner__resend"
        onClick={handleResend}
        disabled={isSending}
      >
        {isSending ? 'Sending...' : 'Resend'}
      </button>
      {message && (
        <span className="verification-banner__message" role="status">
          {message}
        </span>
      )}
    </div>
  )
}