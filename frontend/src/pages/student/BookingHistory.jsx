import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listAll } from '../../api/client'
import { useDialog } from '../../components/Dialog'
import { EmptyState, ErrorState, Loading, PageHeader, SearchBox, StatusBadge, TabPills } from '../../components/ui'
import { formatDateTime } from '../../lib/format'
import { matches } from '../../lib/search'
import { cancelBooking } from '../../lib/staffActions'
import { useAction } from '../../lib/useAction'
import { useApi } from '../../lib/useApi'
import { describeBooking, useResources } from '../../lib/useResources'

const STATUS_LABELS = {
  all: 'ทั้งหมด',
  pending: 'รออนุมัติ',
  confirmed: 'ยืนยันแล้ว',
  rejected: 'ปฏิเสธ',
  cancelled: 'ยกเลิก',
}

export default function BookingHistory() {
  const ask = useDialog()
  const [tab, setTab] = useState('all')
  const [query, setQuery] = useState('')
  const { lookup } = useResources()
  const { data, error, loading, reload } = useApi(() => listAll('/bookings/me'), [])
  const { run, busyKey } = useAction(reload)


  const all = data || []
  const counts = useMemo(() => {
    const c = { all: all.length, pending: 0, confirmed: 0, rejected: 0, cancelled: 0 }
    all.forEach((b) => { if (c[b.status] !== undefined) c[b.status] += 1 })
    return c
  }, [all])

  const TABS = [
    { value: 'all', label: `${STATUS_LABELS.all} (${counts.all})` },
    { value: 'pending', label: `${STATUS_LABELS.pending} (${counts.pending})`, icon: 'fa-clock' },
    { value: 'confirmed', label: `${STATUS_LABELS.confirmed} (${counts.confirmed})`, icon: 'fa-check' },
    { value: 'rejected', label: `${STATUS_LABELS.rejected} (${counts.rejected})`, icon: 'fa-xmark' },
    { value: 'cancelled', label: `${STATUS_LABELS.cancelled} (${counts.cancelled})`, icon: 'fa-ban' },
  ]

  const rows = all
    .map((b) => ({ ...b, item: describeBooking(b, lookup) }))
    .filter((b) => (tab === 'all' || b.status === tab) && matches(query, b.title, b.item.name, b.item.meta))

  return (
    <>
      <PageHeader icon="fa-clock-rotate-left" title="ประวัติการจอง" subtitle="ติดตามและตรวจสอบการจองห้องและอุปกรณ์ของคุณ">
        <Link to="/student/resources" className="button">
          <i className="fa-solid fa-calendar-plus" /> จองใหม่
        </Link>
      </PageHeader>

      <div className="toolbar-container">
        <TabPills tabs={TABS} active={tab} onChange={setTab} />
        <SearchBox value={query} onChange={setQuery} placeholder="ค้นหาการจอง..." />
      </div>

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading ? (
        <Loading />
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th style={{ width: 70 }}>เลขที่</th>
                <th>ประเภท</th>
                <th>รายการ</th>
                <th>เวลาเริ่ม</th>
                <th>เวลาสิ้นสุด</th>
                <th>สถานะ</th>
                <th style={{ width: 110 }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((booking) => (
                <tr key={booking.id}>
                  <td>
                    <strong>#{booking.id}</strong>
                  </td>
                  <td>
                    <span className="status-badge status-in_progress">
                      <i className={`fa-solid ${booking.item.icon}`} /> {booking.item.kind}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>
                    {booking.item.name}{' '}
                    <small className="muted" style={{ fontWeight: 'normal' }}>
                      {booking.item.meta && `(${booking.item.meta})`}
                    </small>
                    <div className="muted" style={{ fontWeight: 'normal', fontSize: '0.8rem' }}>
                      {booking.title}
                    </div>
                    {booking.rejection_reason && (
                      <div className="busy-slot">Rejected: {booking.rejection_reason}</div>
                    )}
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', whiteSpace: 'nowrap' }}>{formatDateTime(booking.start_time)}</td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', whiteSpace: 'nowrap' }}>{formatDateTime(booking.end_time)}</td>
                  <td>
                    <StatusBadge status={booking.status} />
                  </td>
                  <td>
                    {['pending', 'confirmed'].includes(booking.status) && new Date(booking.start_time) > new Date() && (
                      <button
                        type="button"
                        className="button button-sm danger-button"
                        aria-disabled={busyKey !== null || undefined}
                        onClick={() => run(booking.id, () => cancelBooking(ask, booking), `Booking #${booking.id} cancelled`)}
                      >
                        {busyKey === booking.id ? 'Cancelling...' : 'Cancel'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={7}>
                    <EmptyState icon="fa-regular fa-calendar-xmark" title="No Bookings Found" text="You haven't made any reservations that match." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
