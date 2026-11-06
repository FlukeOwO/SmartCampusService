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
        title="หน้าหลัก"
        subtitle={
          <>
            สวัสดี <strong>{user.full_name}</strong> — ดูคำร้อง การจอง และแจ้งเตือนของคุณ
          </>
        }
      >
        <Link to="/student/requests/new" className="button">
          <i className="fa-solid fa-plus" /> ส่งคำร้องใหม่
        </Link>
        <Link to="/student/resources" className="button secondary-button">
          จองห้อง/อุปกรณ์
        </Link>
      </PageHeader>

      {error && <ErrorState error={error} onRetry={reload} />}

      <div className="grid">
        <StatCard
          title="คำร้องของฉัน"
          value={data?.requests.total}
          note={
            data && (
              <div style={{ fontSize: '0.78rem', marginTop: 4 }}>
                <span style={{ color: '#b45309' }}>{data.requests.items.filter(r => r.status === 'pending').length} รอ</span>
                {' · '}
                <span style={{ color: '#0369a1' }}>{data.requests.items.filter(r => r.status === 'in_progress').length} กำลังทำ</span>
              </div>
            )
          }
          icon="fa-bullhorn"
          colors={{ background: 'var(--primary-light)', color: 'var(--primary)', borderColor: 'var(--primary-border)' }}
        >
          <Link to="/student/requests" className="button button-sm secondary-button" style={{ width: '100%' }}>
            ดูทั้งหมด <i className="fa-solid fa-arrow-right" style={{ fontSize: '0.75rem' }} />
          </Link>
        </StatCard>

        <StatCard
          title="การจองของฉัน"
          value={data?.bookings.total}
          note={
            data && (
              <div style={{ fontSize: '0.78rem', marginTop: 4 }}>
                <span style={{ color: '#b45309' }}>{data.bookings.items.filter(b => b.status === 'pending').length} รอ</span>
                {' · '}
                <span style={{ color: '#15803d' }}>{data.bookings.items.filter(b => b.status === 'confirmed').length} ยืนยัน</span>
              </div>
            )
          }
          icon="fa-calendar-check"
          colors={{ background: 'var(--primary-light)', color: 'var(--primary)', borderColor: 'var(--primary-border)' }}
        >
          <Link to="/student/bookings" className="button button-sm secondary-button" style={{ width: '100%' }}>
            ประวัติการจอง <i className="fa-solid fa-arrow-right" style={{ fontSize: '0.75rem' }} />
          </Link>
        </StatCard>

        <StatCard
          title="จองด่วน"
          value={null}
          note={<div className="muted" style={{ fontSize: '0.85rem', marginTop: '0.2rem' }}>ห้องและอุปกรณ์</div>}
          icon="fa-cubes-stacked"
          colors={{ background: '#f5f3ff', color: '#7c3aed', borderColor: '#ddd6fe' }}
        >
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            <Link to="/student/resources?tab=rooms" className="button button-sm" style={{ flex: 1 }}>
              ห้อง
            </Link>
            <Link to="/student/resources?tab=equipment" className="button button-sm secondary-button" style={{ flex: 1 }}>
              อุปกรณ์
            </Link>
          </div>
        </StatCard>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title-row">
            <h2 className="section-title">กิจกรรมล่าสุด</h2>
            <Link to="/student/requests" style={{ fontSize: '0.82rem' }}>
              ดูทั้งหมด
            </Link>
          </div>
          {loading && <Loading />}
          {data && data.requests.items.length + data.bookings.items.length === 0 && (
            <EmptyState compact icon="fa-solid fa-inbox" title="ยังไม่มีกิจกรรม" text="ส่งคำร้องหรือจองห้องเพื่อเริ่มต้น" />
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
            <h2 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              แจ้งเตือน
              {data?.notifications.total > 0 && (
                <span className="count-tag">
                  {data.notifications.total}
                </span>
              )}
            </h2>
            {data?.notifications.total > 0 && (
              <button
                type="button"
                className="button button-sm secondary-button"
                onClick={() => markRead('/notifications/read/all', 'POST')}
              >
                อ่านทั้งหมด
              </button>
            )}
          </div>
          {data && data.notifications.items.length === 0 && (
            <EmptyState compact icon="fa-solid fa-bell" title="ไม่มีแจ้งเตือนใหม่" text="เราจะแจ้งให้คุณทราบเมื่อมีการเปลี่ยนแปลงสถานะคำร้องหรือการจอง" />
          )}
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
                      title="อ่านแล้ว"
                      aria-label="อ่านแล้ว"
                      onClick={() => markRead(`/notifications/${n.id}/read`, 'PATCH')}
                    >
                      <i className="fa-solid fa-check" />
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
