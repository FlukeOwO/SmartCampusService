import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, listAll } from '../../api/client'
import { useFlash } from '../../components/Flash'
import { EmptyState, ErrorState, Loading, PageHeader, SearchBox, StatusBadge, TabPills } from '../../components/ui'
import { formatDateTime } from '../../lib/format'
import { matches } from '../../lib/search'
import { useApi } from '../../lib/useApi'
import { describeBooking, useResources } from '../../lib/useResources'

const TABS = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending', icon: 'fa-clock', color: '#fbbf24' },
  { value: 'confirmed', label: 'Confirmed', icon: 'fa-check', color: '#34d399' },
  { value: 'rejected', label: 'Rejected', icon: 'fa-xmark', color: '#f87171' },
  { value: 'cancelled', label: 'Cancelled', icon: 'fa-ban', color: '#f87171' },
]

export default function BookingHistory() {
  const flash = useFlash()
  const [tab, setTab] = useState('all')
  const [query, setQuery] = useState('')
  const { lookup } = useResources()
  const { data, error, loading, reload } = useApi(() => listAll('/bookings/me'), [])

  const cancel = async (booking) => {
    const reason = window.prompt('Reason for cancelling this booking?')
    if (!reason) return
    try {
      await api(`/bookings/${booking.id}/cancel`, { method: 'PUT', json: { cancellation_reason: reason } })
      flash(`Booking #${booking.id} cancelled`, 'success')
      reload()
    } catch (err) {
      flash(err.message, 'danger')
    }
  }

  const rows = (data || [])
    .map((b) => ({ ...b, item: describeBooking(b, lookup) }))
    .filter((b) => (tab === 'all' || b.status === tab) && matches(query, b.title, b.item.name, b.item.meta))

  return (
    <>
      <PageHeader icon="fa-clock-rotate-left" title="My Booking History" subtitle="Track and review all your room and equipment reservations.">
        <Link to="/student/resources" className="button">
          <i className="fa-solid fa-calendar-plus" /> New Reservation
        </Link>
      </PageHeader>

      <div className="toolbar-container">
        <TabPills tabs={TABS.map((t) => (t.value === 'all' ? { ...t, label: `All (${data?.length ?? 0})` } : t))} active={tab} onChange={setTab} />
        <SearchBox value={query} onChange={setQuery} placeholder="Search reservations..." />
      </div>

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading ? (
        <Loading />
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th style={{ width: 70 }}>ID</th>
                <th>Type</th>
                <th>Reserved Item</th>
                <th>Start Time</th>
                <th>End Time</th>
                <th>Status</th>
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
                      <button type="button" className="button button-sm danger-button" style={{ padding: '0.25rem 0.6rem' }} onClick={() => cancel(booking)}>
                        Cancel
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
