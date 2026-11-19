// src/features/sentences/AddSentenceDialog.jsx
// The global "add a sentence" modal. Mount it to open it; the parent unmounts it to close.
import { useState } from 'react'
import { createSentence } from '../../api/sentences'
import { useDueCount } from '../../context/DueCountContext'
import { useSentencesSync } from '../../context/SentencesSyncContext'
import MethodDialog from '../session/MethodDialog'
import SentenceForm from './SentenceForm'
import './sentences.css'

export default function AddSentenceDialog({ onClose, onImport }) {
  const { notifySentencesChanged } = useSentencesSync()
  const { refresh: refreshDueCount } = useDueCount()
  // Changing the key remounts SentenceForm, which clears its fields.
  const [formKey, setFormKey] = useState(0)
  const [addedCount, setAddedCount] = useState(0)

  async function handleCreate(data) {
    // Errors propagate on purpose: SentenceForm shows its own error message.
    await createSentence(data)
    notifySentencesChanged()
    refreshDueCount()
    setAddedCount((n) => n + 1)
    setFormKey((k) => k + 1)
  }

  return (
    <MethodDialog title="Add a sentence" onClose={onClose} className="add-dialog">
      <h2>Add a sentence</h2>
      {addedCount > 0 && (
        <p className="add-dialog-note" role="status">
          Added ({addedCount} this time). Add another, or close this window.
        </p>
      )}
      <SentenceForm key={formKey} onSubmit={handleCreate} submitLabel="Add sentence" />
      <button type="button" className="btn btn-secondary" onClick={onImport}>
        Import from Excel
      </button>
    </MethodDialog>
  )
}
