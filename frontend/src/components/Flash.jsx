import { createContext, useCallback, useContext, useMemo, useState } from 'react'

/** แทน flash() ของ Flask: แสดงข้อความด้านบนของหน้าแล้วหายเองใน 5 วินาที */
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
    setTimeout(() => setMessages((current) => current.filter((m) => m.id !== id)), 5000)
  }, [])

  const clear = useCallback(() => setMessages([]), [])

  const value = useMemo(() => ({ flash, clear, messages }), [flash, clear, messages])
  return <FlashContext.Provider value={value}>{children}</FlashContext.Provider>
}

export function FlashMessages() {
  const { messages } = useContext(FlashContext)
  return messages.map((m) => (
    <div key={m.id} className={`alert ${m.type}`} role={m.type === 'danger' ? 'alert' : 'status'}>
      <i className={`fa-solid ${ICONS[m.type] || ICONS.info}`} />
      <span>{m.text}</span>
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
