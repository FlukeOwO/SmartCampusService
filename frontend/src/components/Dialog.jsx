import { createContext, useCallback, useContext, useState } from 'react'
import { Modal } from './ui'

/**
 * กล่องยืนยัน/กรอกเหตุผลแทน window.prompt และ window.confirm
 * ask({ title, message, input, required, confirmLabel, danger }) คืน Promise:
 *   - ยืนยัน: ข้อความที่กรอก (ถ้ามีช่อง input) หรือ true
 *   - ยกเลิก: null
 */
const DialogContext = createContext(null)

export function DialogProvider({ children }) {
  const [dialog, setDialog] = useState(null)

  const ask = useCallback((options) => new Promise((resolve) => setDialog({ ...options, resolve, id: Date.now() })), [])

  const done = (value) => {
    dialog.resolve(value)
    setDialog(null)
  }

  return (
    <DialogContext.Provider value={ask}>
      {children}
      {dialog && <DialogView key={dialog.id} dialog={dialog} onDone={done} />}
    </DialogContext.Provider>
  )
}

function DialogView({ dialog, onDone }) {
  const [text, setText] = useState('')
  const { title, message, input, required = false, confirmLabel = 'Confirm', danger = false } = dialog

  const submit = (e) => {
    e.preventDefault()
    if (input && required && !text.trim()) return
    onDone(input ? text.trim() : true)
  }

  return (
    <Modal title={title} icon={danger ? 'fa-triangle-exclamation' : 'fa-circle-question'} onClose={() => onDone(null)}>
      <form onSubmit={submit} className="stack">
        {message && <p className="dialog-message">{message}</p>}
        {input && (
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="dialog-input">{input}</label>
            <textarea id="dialog-input" rows={3} required={required} value={text} onChange={(e) => setText(e.target.value)} />
          </div>
        )}
        <div className="dialog-actions">
          <button type="button" className="button secondary-button" onClick={() => onDone(null)}>
            Go back
          </button>
          <button type="submit" className={`button ${danger ? 'danger-button' : ''}`} disabled={input && required && !text.trim()}>
            {confirmLabel}
          </button>
        </div>
      </form>
    </Modal>
  )
}

// eslint-disable-next-line react/only-export-components
export function useDialog() {
  return useContext(DialogContext)
}
