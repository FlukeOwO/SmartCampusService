import { useState } from 'react'
import { api } from '../api/client'
import { useFlash } from '../components/Flash'
import { EmptyState, ErrorState, Loading, PageHeader, TabPills } from '../components/ui'
import { formatDateTime } from '../lib/format'
import { useApi } from '../lib/useApi'

const notifyChanged = () => window.dispatchEvent(new Event('notifications:changed'))

export default function Notifications() {
  const flash = useFlash()
  const [tab, setTab] = useState('unread')
  const { data, error, loading, reload } = useApi(
    () => api('/notifications', { params: { page_size: 100, unread_only: tab === 'unread' } }),
    [tab],
  )

  const act = async (fn, message) => {
    try {
      await fn()
      if (message) flash(message, 'info')
      notifyChanged()
      reload()
    } catch (err) {
      flash(err.message, 'danger')
    }
  }

  return (
    <>
      <PageHeader icon="fa-bell" title="Notifications" subtitle="Updates about your requests and bookings.">
        <button
          type="button"
          className="button secondary-button"
          onClick={() => act(() => api('/notifications/read/all', { method: 'POST' }), 'All notifications marked as read')}
        >
          <i className="fa-solid fa-check-double" /> Mark All Read
        </button>
      </PageHeader>

      <div className="toolbar-container">
        <TabPills
          active={tab}
          onChange={setTab}
          tabs={[
            { value: 'unread', label: 'Unread' },
            { value: 'all', label: 'All' },
          ]}
        />
      </div>

      <div className="card">
        {loading && <Loading />}
        {error && <ErrorState error={error} onRetry={reload} />}
        {data && data.items.length === 0 && (
          <EmptyState icon="fa-regular fa-bell-slash" title="No notifications" text="You're all caught up." />
        )}
        {data && data.items.length > 0 && (
          <ul className="notification-list">
            {data.items.map((n) => (
              <li key={n.id} className="notification-item" style={n.is_read ? { opacity: 0.6 } : undefined}>
                <div className="notification-msg">
                  <span>
                    <strong>{n.title}</strong> — {n.message}
                  </span>
                </div>
                <div className="notification-actions">
                  <span className="notification-time">{formatDateTime(n.created_at)}</span>
                  {!n.is_read && (
                    <button
                      type="button"
                      className="btn-dismiss"
                      title="Mark as read"
                      aria-label="Mark as read"
                      onClick={() => act(() => api(`/notifications/${n.id}/read`, { method: 'PATCH' }))}
                    >
                      <i className="fa-solid fa-check" />
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn-dismiss"
                    title="Delete"
                    aria-label="Delete notification"
                    onClick={() => act(() => api(`/notifications/${n.id}`, { method: 'DELETE' }))}
                  >
                    <i className="fa-solid fa-xmark" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
}
