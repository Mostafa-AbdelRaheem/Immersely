// src/features/session/MethodDialog.jsx
import { useEffect, useRef } from 'react'
import './MethodDialog.css'

// Shows its children in a native modal <dialog>. Mount it to open it;
// onClose fires when the user dismisses it (Escape, ×, backdrop click).
export default function MethodDialog({ title, busy, onClose, children }) {
  const ref = useRef(null)

  useEffect(() => {
    const dialog = ref.current
    if (dialog && !dialog.open) dialog.showModal()
  }, [])

  function handleCancel(e) {
    if (busy) e.preventDefault() // block Escape while a session is starting
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget && !busy) ref.current.close()
  }

  return (
    <dialog
      ref={ref}
      className="method-dialog"
      aria-label={title}
      onClose={onClose}
      onCancel={handleCancel}
      onClick={handleBackdropClick}
    >
      <div className="method-dialog-body">
        <button
          type="button"
          className="method-dialog-close"
          aria-label="Close"
          disabled={busy}
          onClick={() => ref.current.close()}
        >
          ×
        </button>
        {children}
      </div>
    </dialog>
  )
}