// src/features/sentences/SentenceListItem.jsx
import { useState } from 'react'
import SentenceForm from './SentenceForm'

export default function SentenceListItem({ sentence, onUpdate, onDelete }) {
  const [isEditing, setIsEditing] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  async function handleUpdate(changes) {
    await onUpdate(sentence.id, changes)
    setIsEditing(false)
  }

  async function handleDelete() {
    if (!window.confirm('Delete this sentence?')) return
    setIsDeleting(true)
    try {
      await onDelete(sentence.id)
    } catch (err) {
      setIsDeleting(false)
    }
  }

  if (isEditing) {
    return (
      <SentenceForm
        key={sentence.id}
        initialValues={sentence}
        onSubmit={handleUpdate}
        onCancel={() => setIsEditing(false)}
        submitLabel="Save"
      />
    )
  }

  return (
    <div>
      <p>
        <strong>{sentence.de}</strong> — {sentence.en}
      </p>
      <button onClick={() => setIsEditing(true)} disabled={isDeleting}>
        Edit
      </button>
      <button onClick={handleDelete} disabled={isDeleting}>
        {isDeleting ? 'Deleting…' : 'Delete'}
      </button>
    </div>
  )
}