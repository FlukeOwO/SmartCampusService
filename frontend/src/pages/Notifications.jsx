import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useFlash } from '../components/Flash'
import { EmptyState, ErrorState, Loading, PageHeader, TabPills } from '../components/ui'
import { formatDateTime } from '../lib/format'
import { useApi } from '../lib/useApi'

const notifyChanged = () => window.dispatchEvent(new Event('notifications:changed'))

/** หน้าที่เกี่ยวข้องกับแจ้งเตือน (related_resource_type จาก backend: request / booking) */
function relatedPath(n, isStaff) {
  if (n.related_resource_type === 'request') return isStaff ? '/staff/requests' : '/student/requests'
  if (n.related_resource_type === 'booking') return isStaff ? '/staff/bookings' : '/student/bookings'
  return null
}

export default function Notifications() {
  const flash = useFlash()
  const { isStaff } = useAuth()
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
              <li key={n.id} className={`notification-item ${n.is_read ? 'is-read' : ''}`}>
                <div className="notification-msg">
                  <span>
                    <strong>{n.title}</strong> — {n.message}
                  </span>
                </div>
                <div className="notification-actions">
                  <span className="notification-time">{formatDateTime(n.created_at)}</span>
                  {relatedPath(n, isStaff) && (
                    <Link to={relatedPath(n, isStaff)} className="button button-sm secondary-button">
                      View
                    </Link>
                  )}
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
                    <i className="fa-solid fa-trash-can" />
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
