// src/features/read/ArticleDialog.jsx
import { useEffect, useRef } from 'react'
import './ArticleDialog.css'

// Native <dialog> shown as a modal. Mounted only while an article is open,
// so showModal() runs once on mount. Escape, the × button and a backdrop
// click all close it, and all are blocked while isBusy (e.g. deleting).
export default function ArticleDialog({ title, isBusy, onClose, children }) {
  const ref = useRef(null)

  useEffect(() => {
    const dialog = ref.current
    if (dialog && !dialog.open) dialog.showModal()
  }, [])

  function handleCancel(e) {
    e.preventDefault() // we close by unmounting, not by the browser
    if (!isBusy) onClose()
  }

  function handleClick(e) {
    // A click on the <dialog> element itself (not its inner box) is the backdrop.
    if (e.target === ref.current && !isBusy) onClose()
  }

  return (
    <dialog
      ref={ref}
      className="article-dialog"
      aria-label={title}
      onCancel={handleCancel}
      onClick={handleClick}
    >
      <div className="article-dialog-inner">
        <button
          type="button"
          className="article-dialog-close"
          aria-label="Close"
          disabled={isBusy}
          onClick={onClose}
        >
          ×
        </button>
        {children}
      </div>
    </dialog>
  )
}