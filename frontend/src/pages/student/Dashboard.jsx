import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { useFlash } from '../../components/Flash'
import { EmptyState, ErrorState, Loading, PageHeader, StatCard, StatusBadge } from '../../components/ui'
import { formatShort } from '../../lib/format'
import { useApi } from '../../lib/useApi'
import { describeBooking, useResources } from '../../lib/useResources'

export default function StudentDashboard() {
  const { user } = useAuth()
  const flash = useFlash()
  const { lookup } = useResources()
  const { data, error, loading, reload } = useApi(async () => {
    const [requests, bookings, notifications] = await Promise.all([
      api('/requests/me', { params: { page_size: 3 } }),
      api('/bookings/me', { params: { page_size: 3 } }),
      api('/notifications', { params: { unread_only: true, page_size: 10 } }),
    ])
    return { requests, bookings, notifications }
  }, [])

  const markRead = async (path, method) => {
    try {
      await api(path, { method })
      window.dispatchEvent(new Event('notifications:changed'))
      reload()
    } catch (err) {
      flash(err.message, 'danger')
    }
  }

  return (
    <>
      <PageHeader
        title="Student Dashboard"
        subtitle={
          <>
            Welcome back, <strong>{user.full_name}</strong>. Here is your campus activity overview.
          </>
        }
      >
        <Link to="/student/requests/new" className="button">
          <i className="fa-solid fa-plus" /> New Request
        </Link>
        <Link to="/student/resources" className="button secondary-button">
          Book Resource
        </Link>
      </PageHeader>

      {error && <ErrorState error={error} onRetry={reload} />}

      <div className="grid">
        <StatCard
          title="My Requests"
          value={data?.requests.total}
          icon="fa-bullhorn"
          colors={{ background: '#eff6ff', color: '#2563eb', borderColor: '#bfdbfe' }}
        >
          <Link to="/student/requests" className="button button-sm secondary-button" style={{ width: '100%' }}>
            View All Requests <i className="fa-solid fa-arrow-right" style={{ fontSize: '0.75rem' }} />
          </Link>
        </StatCard>

        <StatCard
          title="My Bookings"
          value={data?.bookings.total}
          icon="fa-calendar-check"
          colors={{ background: '#ecfeff', color: '#0891b2', borderColor: '#a5f3fc' }}
        >
          <Link to="/student/bookings" className="button button-sm secondary-button" style={{ width: '100%' }}>
            View Booking History <i className="fa-solid fa-arrow-right" style={{ fontSize: '0.75rem' }} />
          </Link>
        </StatCard>

        <StatCard
          title="Quick Booking"
          value={null}
          note={<div className="muted" style={{ fontSize: '0.85rem', marginTop: '0.2rem' }}>Reserve rooms &amp; equipment</div>}
          icon="fa-cubes-stacked"
          colors={{ background: '#f5f3ff', color: '#7c3aed', borderColor: '#ddd6fe' }}
        >
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            <Link to="/student/resources?tab=rooms" className="button button-sm" style={{ flex: 1 }}>
              Rooms
            </Link>
            <Link to="/student/resources?tab=equipment" className="button button-sm secondary-button" style={{ flex: 1 }}>
              Equipment
            </Link>
          </div>
        </StatCard>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title-row">
            <h3>Recent Activity</h3>
            <Link to="/student/requests" style={{ fontSize: '0.82rem' }}>
              View all
            </Link>
          </div>
          {loading && <Loading />}
          {data && data.requests.items.length + data.bookings.items.length === 0 && (
            <EmptyState compact text="No recent requests or bookings." />
          )}
          {data && (
            <div className="stack">
              {data.requests.items.map((req) => (
                <div key={`r${req.id}`} className="list-item">
                  <div>
                    <div className="list-item-title">{req.title}</div>
                    <small className="muted">{req.request_number}</small>
                  </div>
                  <StatusBadge status={req.status} />
                </div>
              ))}
              {data.bookings.items.map((b) => (
                <div key={`b${b.id}`} className="list-item">
                  <div>
                    <div className="list-item-title">{describeBooking(b, lookup).name}</div>
                    <small className="muted">{formatShort(b.start_time)}</small>
                  </div>
                  <StatusBadge status={b.status} />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title-row">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              Notifications
              {data?.notifications.total > 0 && (
                <span className="role-tag" style={{ fontSize: '0.68rem' }}>
                  {data.notifications.total}
                </span>
              )}
            </h3>
            {data?.notifications.total > 0 && (
              <button
                type="button"
                className="button button-sm secondary-button"
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                onClick={() => markRead('/notifications/read/all', 'POST')}
              >
                Mark All Read
              </button>
            )}
          </div>
          {data && data.notifications.items.length === 0 && <EmptyState compact text="No unread notifications." />}
          {data && data.notifications.items.length > 0 && (
            <ul className="notification-list">
              {data.notifications.items.map((n) => (
                <li key={n.id} className="notification-item">
                  <div className="notification-msg">
                    <span>{n.message}</span>
                  </div>
                  <div className="notification-actions">
                    <span className="notification-time">{formatShort(n.created_at)}</span>
                    <button
                      type="button"
                      className="btn-dismiss"
                      title="Dismiss"
                      aria-label="Mark as read"
                      onClick={() => markRead(`/notifications/${n.id}/read`, 'PATCH')}
                    >
                      <i className="fa-solid fa-xmark" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  )
}
