import { useEffect } from 'react'
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
      {title && <h3>{title}</h3>}
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
          <h3>{title}</h3>
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

export function Modal({ title, icon, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-container" role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-header">
          <h3>
            {icon && <i className={`fa-solid ${icon}`} style={{ color: 'var(--primary)' }} />} {title}
          </h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}
