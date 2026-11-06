import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { useDialog } from '../../components/Dialog'
import { ActionButton, EmptyState, ErrorState, Loading, PageHeader, StatCard } from '../../components/ui'
import { formatDuration, formatShort, statusLabel } from '../../lib/format'
import { REQUEST_ACTION, approveBooking, rejectBooking, updateRequestStatus } from '../../lib/staffActions'
import { useAction } from '../../lib/useAction'
import { useApi } from '../../lib/useApi'
import { describeBooking, useResources } from '../../lib/useResources'

export default function StaffDashboard() {
  const ask = useDialog()
  const { rooms, equipments, lookup } = useResources()
  const { data, error, loading, reload } = useApi(async () => {
    const [summary, requests, bookings] = await Promise.all([
      api('/dashboard/summary', { params: { days: 30 } }),
      api('/requests', { params: { status: 'pending', page_size: 5 } }),
      api('/bookings', { params: { status: 'pending', page_size: 5 } }),
    ])
    return { summary, requests, bookings }
  }, [])

  const { run, busyKey } = useAction(reload)

  const s = data?.summary
  const pendingRequests = s?.requests.by_status.pending ?? 0
  const pendingBookings = s?.bookings.pending_approval ?? 0

  return (
    <>
      <PageHeader title="งานที่ต้องทำ" subtitle="รวมคำร้องและการจองที่รออนุมัติ กดเพื่อดำเนินการได้เลย">
        <Link to="/staff/requests?status=pending" className="button">
          <i className="fa-solid fa-clock" /> {pendingRequests} คำร้องรอ
        </Link>
        <Link to="/staff/bookings?status=pending" className="button secondary-button">
          <i className="fa-solid fa-calendar-check" /> {pendingBookings} การจองรอ
        </Link>
      </PageHeader>

      {error && <ErrorState error={error} onRetry={reload} />}

      <div className="grid">
        <StatCard
          title="คำร้อง"
          value={s?.requests.total}
          note={<small style={{ color: '#b45309', fontWeight: 600 }}>{pendingRequests} รอ · {s?.requests.open_unassigned ?? 0} ยังไม่มอบหมาย</small>}
          icon="fa-clipboard-list"
          colors={{ background: '#eff6ff', color: '#2563eb', borderColor: '#bfdbfe' }}
        >
          <Link to="/staff/requests" className="button button-sm secondary-button" style={{ width: '100%' }}>
            จัดการคำร้อง <i className="fa-solid fa-arrow-right" style={{ fontSize: '0.75rem' }} />
          </Link>
        </StatCard>
        <StatCard
          title="การจอง"
          value={s?.bookings.total}
          note={<small style={{ color: '#b45309', fontWeight: 600 }}>{pendingBookings} รอ · {s?.bookings.upcoming_confirmed ?? 0} กำลังมาถึง</small>}
          icon="fa-calendar-check"
          colors={{ background: '#ecfeff', color: '#0891b2', borderColor: '#a5f3fc' }}
        >
          <Link to="/staff/bookings" className="button button-sm secondary-button" style={{ width: '100%' }}>
            จัดการจอง <i className="fa-solid fa-arrow-right" style={{ fontSize: '0.75rem' }} />
          </Link>
        </StatCard>
        <StatCard
          title="ห้อง"
          value={rooms.length}
          note={<small className="muted">ห้องที่ตั้งค่าไว้</small>}
          icon="fa-door-open"
          colors={{ background: '#f0fdf4', color: '#16a34a', borderColor: '#bbf7d0' }}
        >
          <Link to="/staff/rooms" className="button button-sm secondary-button" style={{ width: '100%' }}>
            จัดการห้อง <i className="fa-solid fa-arrow-right" style={{ fontSize: '0.75rem' }} />
          </Link>
        </StatCard>
        <StatCard
          title="อุปกรณ์"
          value={equipments.length}
          note={<small className="muted">รายการทั้งหมด</small>}
          icon="fa-boxes-stacked"
          colors={{ background: '#f5f3ff', color: '#7c3aed', borderColor: '#ddd6fe' }}
        >
          <Link to="/staff/equipment" className="button button-sm secondary-button" style={{ width: '100%' }}>
            จัดการอุปกรณ์ <i className="fa-solid fa-arrow-right" style={{ fontSize: '0.75rem' }} />
          </Link>
        </StatCard>
      </div>

      {loading && <Loading />}

      {data && (
        <div className="grid grid-2">
          <div className="card">
            <div className="card-title-row">
              <h2 className="section-title">คำร้องรออนุมัติ</h2>
              <Link to="/staff/requests?status=pending" style={{ fontSize: '0.82rem' }}>
                ดูทั้งหมด
              </Link>
            </div>
            {data.requests.items.length === 0 ? (
              <EmptyState compact text="ไม่มีคำร้องรอ" />
            ) : (
              <div className="stack">
                {data.requests.items.map((req) => (
                  <div key={req.id} className="list-item">
                    <div>
                      <div className="list-item-title">
                        {req.request_number} {req.title}
                      </div>
                      <small className="muted">
                        {statusLabel(req.request_type)} · {req.priority} · {formatShort(req.created_at)}
                      </small>
                    </div>
                    <div className="quick-action-group">
                      {['in_progress', 'rejected'].map((next) => (
                        <ActionButton
                          key={next}
                          {...REQUEST_ACTION[next]}
                          label={`${REQUEST_ACTION[next].title}: ${req.request_number}`}
                          busy={busyKey === `r${req.id}:${next}`}
                          disabled={busyKey !== null}
                          onClick={() => run(`r${req.id}:${next}`, () => updateRequestStatus(ask, req, next), `${req.request_number}: ${statusLabel(next)}`)}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-title-row">
              <h2 className="section-title">การจองรออนุมัติ</h2>
              <Link to="/staff/bookings?status=pending" style={{ fontSize: '0.82rem' }}>
                ดูทั้งหมด
              </Link>
            </div>
            {data.bookings.items.length === 0 ? (
              <EmptyState compact text="ไม่มีการจองรอ" />
            ) : (
              <div className="stack">
                {data.bookings.items.map((b) => (
                  <div key={b.id} className="list-item">
                    <div>
                      <div className="list-item-title">
                        #{b.id} {describeBooking(b, lookup).name}
                      </div>
                      <small className="muted">
                        {b.title} · {formatShort(b.start_time)}
                      </small>
                    </div>
                    <div className="quick-action-group">
                      <ActionButton icon="fa-check" className="btn-approve" label={`อนุมัติการจอง #${b.id}`}
                        busy={busyKey === `b${b.id}:approve`} disabled={busyKey !== null}
                        onClick={() => run(`b${b.id}:approve`, () => approveBooking(b.id), `อนุมัติการจอง #${b.id} แล้ว`)} />
                      <ActionButton icon="fa-xmark" className="btn-reject" label={`ปฏิเสธการจอง #${b.id}`}
                        busy={busyKey === `b${b.id}:reject`} disabled={busyKey !== null}
                        onClick={() => run(`b${b.id}:reject`, () => rejectBooking(ask, b), `ปฏิเสธการจอง #${b.id} แล้ว`)} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="section-title" style={{ marginBottom: '0.85rem' }}>ห้องยอดนิยม (30 วันล่าสุด)</h2>
            {s.top_rooms.length === 0 ? (
              <EmptyState compact text="ยังไม่มีการจองห้อง" />
            ) : (
              <div className="stack">
                {s.top_rooms.map((room) => (
                  <div key={room.room_id} className="list-item">
                    <span className="list-item-title">
                      {room.room_number} {room.room_name}
                    </span>
                    <span className="count-tag">
                      {room.bookings} ครั้ง
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="section-title" style={{ marginBottom: '0.85rem' }}>คำร้องตามสถานะ</h2>
            <div className="stack">
              {Object.entries(s.requests.by_status).map(([status, count]) => (
                <div key={status} className="list-item">
                  <span className={`status-badge status-${status}`}>{statusLabel(status)}</span>
                  <strong>{count}</strong>
                </div>
              ))}
              {s.requests.avg_resolution_hours !== null && (
                <small className="muted">เวลาเฉลี่ยเฉลี่ยบัญหา: {formatDuration(s.requests.avg_resolution_hours)}</small>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
