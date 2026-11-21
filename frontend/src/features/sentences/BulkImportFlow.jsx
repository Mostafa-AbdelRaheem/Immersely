// src/features/sentences/BulkImportFlow.jsx
// The whole bulk import flow in a modal: pick a file, review/edit the parsed
// rows, save. Mount it to open it; the parent unmounts it to close.
import { useRef, useState } from 'react'
import { useTopics } from '../../context/TopicsContext'
import {
  confirmImport,
  downloadImportTemplate,
  previewImport,
} from '../../api/sentences'
import MethodDialog from '../session/MethodDialog'
import PreviewRowEditor from './PreviewRowEditor'
import {
  describeConfirmError,
  describeImportError,
  recheckRows,
} from './importLogic'
import './sentences.css'

const TEMPLATE_FILENAME = 'immersely_import_template.xlsx'

export default function BulkImportFlow({ onClose, onImported }) {
  const { topics } = useTopics()
  const [stage, setStage] = useState('pick') // pick | previewing | review | saving
  const [rows, setRows] = useState([])
  const [maxLen, setMaxLen] = useState(0)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const blockedCount = rows.filter((r) => r.has_blocking_issue).length
  const canConfirm = stage === 'review' && rows.length > 0 && blockedCount === 0

  async function handleFileChosen(e) {
    const file = e.target.files[0]
    if (!file) return
    setError(null)
    setStage('previewing')
    try {
      const data = await previewImport(file)
      setRows(data.rows)
      setMaxLen(data.max_len)
      setStage('review')
    } catch (err) {
      setError(describeImportError(err))
      setStage('pick')
    } finally {
      // Lets the user pick the same file again after fixing it.
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  function handleRowChange(rowNumber, patch) {
    setRows((prev) =>
      recheckRows(
        prev.map((r) => (r.row_number === rowNumber ? { ...r, ...patch } : r)),
        maxLen,
      ),
    )
  }

  function handleRowRemove(rowNumber) {
    setRows((prev) =>
      recheckRows(
        prev.filter((r) => r.row_number !== rowNumber),
        maxLen,
      ),
    )
  }

  async function handleConfirm() {
    if (!canConfirm) return
    setError(null)
    setStage('saving')
    try {
      const payload = rows.map((r) => ({
        de: r.de,
        en: r.en,
        topics: r.topics,
        grammar_tag: r.grammar_tag || null,
      }))
      const saved = await confirmImport(payload)
      onImported(saved)
    } catch (err) {
      setError(describeConfirmError(err))
      setStage('review')
    }
  }

  async function handleDownloadTemplate() {
    setError(null)
    try {
      const blob = await downloadImportTemplate()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = TEMPLATE_FILENAME
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      setError("Couldn't download the template. Please try again.")
    }
  }

  return (
    <MethodDialog
      title="Import sentences"
      busy={stage === 'saving'}
      onClose={onClose}
      className="import-dialog"
    >
      <h2>Import sentences</h2>

      {error && <p className="form-error">{error}</p>}

      {(stage === 'pick' || stage === 'previewing') && (
        <div className="import-pick">
          <p>
            Upload an .xlsx file with columns named <strong>de</strong> and{' '}
            <strong>en</strong>.
          </p>
          <input
            ref={fileInputRef}
            className="import-file"
            type="file"
            accept=".xlsx"
            aria-label="Choose an .xlsx file"
            disabled={stage === 'previewing'}
            onChange={handleFileChosen}
          />
          {stage === 'previewing' && <p>Reading and tagging your file…</p>}
          <button type="button" className="btn btn-secondary" onClick={handleDownloadTemplate}>
            Download template
          </button>
        </div>
      )}

      {(stage === 'review' || stage === 'saving') && (
        <>
          <div className="import-rows">
            {rows.map((r) => (
              <PreviewRowEditor
                key={r.row_number}
                row={r}
                allTopics={topics}
                onChange={handleRowChange}
                onRemove={handleRowRemove}
              />
            ))}
          </div>

          <div className="import-footer">
            {rows.length === 0 && <p>No rows left to import.</p>}
            {blockedCount > 0 && (
              <p>
                {blockedCount} {blockedCount === 1 ? 'row needs' : 'rows need'} fixing
              </p>
            )}
            <button type="button" className="btn btn-primary" disabled={!canConfirm} onClick={handleConfirm}>
              {stage === 'saving'
                ? 'Saving…'
                : `Import ${rows.length} ${rows.length === 1 ? 'sentence' : 'sentences'}`}
            </button>
          </div>
        </>
      )}
    </MethodDialog>
  )
}
