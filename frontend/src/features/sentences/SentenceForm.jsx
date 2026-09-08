// src/features/sentences/SentenceForm.jsx
import { useState } from 'react'

export default function SentenceForm({ initialValues, onSubmit, onCancel, submitLabel }) {
  const [de, setDe] = useState(initialValues?.de ?? '')
  const [en, setEn] = useState(initialValues?.en ?? '')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const isValid = de.trim().length > 0 && en.trim().length > 0

  async function handleSubmit(e) {
    e.preventDefault()
    if (!isValid || isSubmitting) return

    setIsSubmitting(true)
    setError(null)
    try {
      await onSubmit({ de: de.trim(), en: en.trim() })
    } catch (err) {
      setError('Something went wrong. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="de">German</label>
        <input
          id="de"
          type="text"
          value={de}
          onChange={(e) => setDe(e.target.value)}
          disabled={isSubmitting}
        />
      </div>
      <div>
        <label htmlFor="en">English</label>
        <input
          id="en"
          type="text"
          value={en}
          onChange={(e) => setEn(e.target.value)}
          disabled={isSubmitting}
        />
      </div>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <button type="submit" disabled={!isValid || isSubmitting}>
        {submitLabel ?? 'Save'}
      </button>
      {onCancel && (
        <button type="button" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </button>
      )}
    </form>
  )
}