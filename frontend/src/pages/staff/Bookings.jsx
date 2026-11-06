import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listAll } from '../../api/client'
import { useDialog } from '../../components/Dialog'
import { ActionButton, EmptyState, ErrorState, Loading, PageHeader, SearchBox, StatusBadge, TabPills } from '../../components/ui'
import { formatDateTime } from '../../lib/format'
import { approveBooking, cancelBooking, rejectBooking } from '../../lib/staffActions'
import { useAction } from '../../lib/useAction'
import { matches } from '../../lib/search'
import { useApi } from '../../lib/useApi'
import { describeBooking, useResources } from '../../lib/useResources'

const TABS = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending', icon: 'fa-clock', color: '#fbbf24' },
  { value: 'confirmed', label: 'Confirmed', icon: 'fa-check', color: '#34d399' },
  { value: 'rejected', label: 'Rejected', icon: 'fa-xmark', color: '#f87171' },
  { value: 'cancelled', label: 'Cancelled', icon: 'fa-ban', color: '#94a3b8' },
]

export default function StaffBookings() {
  const ask = useDialog()
  const { lookup } = useResources()
  const [params, setParams] = useSearchParams()
  const status = params.get('status') || 'all'
  const [query, setQuery] = useState('')
  const { data, error, loading, reload } = useApi(
    () => listAll('/bookings', status === 'all' ? {} : { status }),
    [status],
  )

  const { run, busyKey } = useAction(reload)

  const rows = (data || [])
    .map((b) => ({ ...b, item: describeBooking(b, lookup) }))
    .filter((b) => matches(query, b.title, b.item.name, b.item.meta, b.user_name))

  return (
    <>
      <PageHeader icon="fa-calendar-days" title="Booking Management" subtitle="Review, approve, and manage room and equipment reservations." />

      <div className="toolbar-container">
        <TabPills tabs={TABS} active={status} onChange={(value) => setParams(value === 'all' ? {} : { status: value })} />
        <SearchBox value={query} onChange={setQuery} placeholder="Search bookings..." />
      </div>

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading ? (
        <Loading />
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th style={{ width: 60 }}>ID</th>
                <th>Booked By</th>
                <th>Resource</th>
                <th>Start Time</th>
                <th>End Time</th>
                <th>Status</th>
                <th style={{ width: 150 }}>Quick Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((booking) => (
                <tr key={booking.id}>
                  <td>
                    <strong>#{booking.id}</strong>
                  </td>
                  <td style={{ fontWeight: 600 }}>{booking.user_name || `User #${booking.user_id}`}</td>
                  <td>
                    <div>
                      <span className="status-badge status-in_progress" style={{ fontSize: '0.72rem' }}>
                        {booking.item.kind}
                      </span>
                      <strong style={{ marginLeft: 4 }}>{booking.item.name}</strong>
                    </div>
                    <small className="muted">
                      {booking.title}
                      {booking.attendees_count ? ` · ${booking.attendees_count} people` : ''}
                    </small>
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', whiteSpace: 'nowrap' }}>{formatDateTime(booking.start_time)}</td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', whiteSpace: 'nowrap' }}>{formatDateTime(booking.end_time)}</td>
                  <td>
                    <StatusBadge status={booking.status} />
                  </td>
                  <td>
                    <div className="quick-action-group">
                      {booking.status === 'pending' && (
                        <>
                          <ActionButton icon="fa-check" className="btn-approve" label={`Approve booking #${booking.id}`}
                            busy={busyKey === `${booking.id}:approve`} disabled={busyKey !== null}
                            onClick={() => run(`${booking.id}:approve`, () => approveBooking(booking.id), `Booking #${booking.id} approved`)} />
                          <ActionButton icon="fa-xmark" className="btn-reject" label={`Reject booking #${booking.id}`}
                            busy={busyKey === `${booking.id}:reject`} disabled={busyKey !== null}
                            onClick={() => run(`${booking.id}:reject`, () => rejectBooking(ask, booking), `Booking #${booking.id} rejected`)} />
                        </>
                      )}
                      {['pending', 'confirmed'].includes(booking.status) && (
                        <button type="button" className="button button-sm danger-button" aria-disabled={busyKey !== null || undefined}
                          onClick={() => run(`${booking.id}:cancel`, () => cancelBooking(ask, booking), `Booking #${booking.id} cancelled`)}>
                          Cancel
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={7}>
                    <EmptyState icon="fa-regular fa-calendar-xmark" title="No Bookings Found" text="No reservations match the selected filter." />
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
