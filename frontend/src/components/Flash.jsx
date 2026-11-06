import { createContext, useCallback, useContext, useMemo, useState } from 'react'

/** แทน flash() ของ Flask: ข้อความสำเร็จ/ข้อมูลหายเองใน 5 วินาที ส่วน error ค้างไว้จนกว่าผู้ใช้จะปิด */
const FlashContext = createContext(null)

const ICONS = {
  success: 'fa-circle-check',
  danger: 'fa-circle-exclamation',
  info: 'fa-circle-info',
}

export function FlashProvider({ children }) {
  const [messages, setMessages] = useState([])

  const flash = useCallback((text, type = 'info') => {
    const id = Date.now() + Math.random()
    setMessages((current) => [...current, { id, text, type }])
    if (type !== 'danger') setTimeout(() => setMessages((current) => current.filter((m) => m.id !== id)), 5000)
  }, [])

  const clear = useCallback(() => setMessages([]), [])
  const dismiss = useCallback((id) => setMessages((current) => current.filter((m) => m.id !== id)), [])

  const value = useMemo(() => ({ flash, clear, dismiss, messages }), [flash, clear, dismiss, messages])
  return <FlashContext.Provider value={value}>{children}</FlashContext.Provider>
}

export function FlashMessages() {
  const { messages, dismiss } = useContext(FlashContext)
  return messages.map((m) => (
    <div key={m.id} className={`alert ${m.type}`} role={m.type === 'danger' ? 'alert' : 'status'}>
      <i className={`fa-solid ${ICONS[m.type] || ICONS.info}`} />
      <span className="alert-text">{m.text}</span>
      <button type="button" className="alert-close" aria-label="Dismiss message" onClick={() => dismiss(m.id)}>
        <i className="fa-solid fa-xmark" />
      </button>
    </div>
  ))
}

// eslint-disable-next-line react/only-export-components
export function useFlash() {
  return useContext(FlashContext).flash
}

// eslint-disable-next-line react/only-export-components
export function useClearFlash() {
  return useContext(FlashContext).clear
}
