import { useEffect, useRef } from 'react'
import { statusLabel } from '../lib/format'

export function StatusBadge({ status }) {
  return <span className={`status-badge status-${status}`}>{statusLabel(status)}</span>
}

export function Loading({ text = 'Loading...' }) {
  return (
    <div className="loading-state">
      <i className="fa-solid fa-spinner fa-spin" /> {text}
    </div>
  )
}

export function EmptyState({ icon = 'fa-regular fa-clipboard', title, text, compact = false }) {
  return (
    <div className="empty-state" style={compact ? { padding: '1.5rem 1rem' } : undefined}>
      {!compact && (
        <div className="empty-state-icon">
          <i className={icon} />
        </div>
      )}
      {title && <h2>{title}</h2>}
      {text && <p style={compact ? { fontSize: '0.85rem' } : undefined}>{text}</p>}
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="alert danger" role="alert">
      <i className="fa-solid fa-circle-exclamation" />
      <span>{error?.message || 'Something went wrong'}</span>
      {onRetry && (
        <button type="button" className="button button-sm secondary-button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}

export function PageHeader({ icon, title, subtitle, children }) {
  return (
    <div className="page-header">
      <div>
        <h1>
          {icon && <i className={`fa-solid ${icon}`} style={{ color: 'var(--primary)' }} />} {title}
        </h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {children && <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>{children}</div>}
    </div>
  )
}

export function SearchBox({ value, onChange, placeholder }) {
  return (
    <div className="search-box">
      <i className="fa-solid fa-magnifying-glass" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
      />
    </div>
  )
}

export function TabPills({ tabs, active, onChange }) {
  return (
    <div className="tab-pills" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          type="button"
          role="tab"
          aria-selected={active === tab.value}
          className={`tab-pill ${active === tab.value ? 'active' : ''}`}
          onClick={() => onChange(tab.value)}
        >
          {tab.icon && <i className={`fa-solid ${tab.icon}`} style={{ color: tab.color }} />}{' '}
          {tab.label}
        </button>
      ))}
    </div>
  )
}

export function StatCard({ title, value, note, icon, colors, children }) {
  return (
    <div className="card">
      <div className="stat-card">
        <div className="stat-info">
          <h2>{title}</h2>
          {value !== null && <div className="number">{value ?? '–'}</div>}
          {note}
        </div>
        <div className="stat-icon" style={colors}>
          <i className={`fa-solid ${icon}`} />
        </div>
      </div>
      {children && <div className="card-actions">{children}</div>}
    </div>
  )
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

export function Modal({ title, icon, onClose, children }) {
  const boxRef = useRef(null)

  // ย้ายโฟกัสเข้า dialog ตอนเปิด และคืนโฟกัสให้ปุ่มที่กดเปิดตอนปิด
  useEffect(() => {
    const previous = document.activeElement
    const box = boxRef.current
    const target = box.querySelector('.modal-body input, .modal-body select, .modal-body textarea') || box
    target.focus()
    return () => previous?.focus?.()
  }, [])

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
      if (e.key !== 'Tab') return
      // วนโฟกัสอยู่ใน dialog ไม่หลุดไปหน้าหลังฉาก
      const items = [...boxRef.current.querySelectorAll(FOCUSABLE)]
      if (items.length === 0) return
      const first = items[0]
      const last = items[items.length - 1]
      if (e.shiftKey && (document.activeElement === first || document.activeElement === boxRef.current)) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={boxRef} className="modal-container" role="dialog" aria-modal="true" aria-labelledby="modal-title" tabIndex={-1}>
        <div className="modal-header">
          <h2 id="modal-title">
            {icon && <i className={`fa-solid ${icon}`} style={{ color: 'var(--primary)' }} />} {title}
          </h2>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            <i className="fa-solid fa-xmark" />
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}

/**
 * ปุ่มไอคอนสำหรับการกระทำด่วน: แสดง spinner ระหว่างรอ
 * ใช้ aria-disabled แทน disabled เพื่อให้โฟกัสกลับมาที่ปุ่มได้หลังปิด dialog
 */
export function ActionButton({ icon, className, label, busy, disabled, onClick }) {
  const off = busy || disabled
  return (
    <button
      type="button"
      className={`btn-icon ${className}`}
      title={label}
      aria-label={label}
      aria-disabled={off || undefined}
      aria-busy={busy || undefined}
      onClick={off ? undefined : onClick}
    >
      <i className={`fa-solid ${busy ? 'fa-circle-notch fa-spin' : icon}`} />
    </button>
  )
}

/** Drawer ด้านขวา สำหรับดูรายละเอียดโดยไม่เปลี่ยนหน้า */
export function Drawer({ title, onClose, children, wide = false }) {
  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div
        className={`drawer-panel ${wide ? 'drawer-wide' : ''}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="drawer-header">
          <h2 style={{ margin: 0, fontSize: '1.05rem' }}>{title}</h2>
          <button type="button" className="btn-dismiss" onClick={onClose} aria-label="ปิด">
            <i className="fa-solid fa-xmark" />
          </button>
        </div>
        <div className="drawer-body">{children}</div>
      </div>
    </div>
  )
}
