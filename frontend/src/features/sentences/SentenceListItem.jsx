// src/features/sentences/SentenceListItem.jsx
import { useState } from 'react'
import SentenceForm from './SentenceForm'
import TagEditor from './TagEditor'

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
    <div className="sentence-card">
      <p className="sentence-text">
        <strong>{sentence.de}</strong> <span className="en">— {sentence.en}</span>
      </p>
      <TagEditor sentence={sentence} onUpdate={onUpdate} />
      <div className="actions">
        <button className="btn btn-secondary" onClick={() => setIsEditing(true)} disabled={isDeleting}>
          Edit
        </button>
        <button className="btn btn-danger" onClick={handleDelete} disabled={isDeleting}>
          {isDeleting ? 'Deleting…' : 'Delete'}
        </button>
      </div>
    </div>
  )
}