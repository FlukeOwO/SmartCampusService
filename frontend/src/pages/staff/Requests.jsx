import { Fragment, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listAll } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { useFlash } from '../../components/Flash'
import RequestDetail from '../../components/RequestDetail'
import { EmptyState, ErrorState, Loading, PageHeader, SearchBox, StatusBadge, TabPills } from '../../components/ui'
import { formatDateTime, statusLabel } from '../../lib/format'
import { REQUEST_NEXT, assignRequest, updateRequestStatus } from '../../lib/staffActions'
import { matches } from '../../lib/search'
import { useApi } from '../../lib/useApi'
import { useUserNames } from '../../lib/useUserNames'

const TABS = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending', icon: 'fa-clock', color: '#fbbf24' },
  { value: 'in_progress', label: 'In Progress', icon: 'fa-spinner', color: '#38bdf8' },
  { value: 'completed', label: 'Completed', icon: 'fa-check', color: '#34d399' },
  { value: 'rejected', label: 'Rejected', icon: 'fa-xmark', color: '#f87171' },
  { value: 'cancelled', label: 'Cancelled', icon: 'fa-ban', color: '#94a3b8' },
]

const ACTION = {
  in_progress: { icon: 'fa-spinner', className: 'btn-progress', title: 'Start progress' },
  completed: { icon: 'fa-check', className: 'btn-approve', title: 'Mark completed' },
  rejected: { icon: 'fa-xmark', className: 'btn-reject', title: 'Reject request' },
}

export default function StaffRequests() {
  const { user } = useAuth()
  const flash = useFlash()
  const userName = useUserNames()
  const [params, setParams] = useSearchParams()
  const status = params.get('status') || 'all'
  const [query, setQuery] = useState('')
  const [openId, setOpenId] = useState(null)
  const { data, error, loading, reload } = useApi(
    () => listAll('/requests', status === 'all' ? {} : { status }),
    [status],
  )

  const act = async (promise, message) => {
    if (!promise) return
    try {
      await promise
      flash(message, 'success')
      reload()
    } catch (err) {
      flash(err.message, 'danger')
    }
  }

  const rows = (data || []).filter((r) => matches(query, r.title, r.request_number, r.request_type, userName(r.user_id)))

  return (
    <>
      <PageHeader icon="fa-list-check" title="Request Management" subtitle="Review, assign, update, and resolve campus service requests." />

      <div className="toolbar-container">
        <TabPills tabs={TABS} active={status} onChange={(value) => setParams(value === 'all' ? {} : { status: value })} />
        <SearchBox value={query} onChange={setQuery} placeholder="Search requests..." />
      </div>

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading ? (
        <Loading />
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th style={{ width: 150 }}>Number</th>
                <th>Requester</th>
                <th>Title</th>
                <th>Priority</th>
                <th>Status</th>
                <th style={{ width: 210 }}>Quick Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => (
                <Fragment key={item.id}>
                  <tr>
                    <td>
                      <strong>{item.request_number}</strong>
                      <div className="muted" style={{ fontSize: '0.78rem' }}>
                        {formatDateTime(item.created_at)}
                      </div>
                    </td>
                    <td style={{ fontWeight: 600 }}>{userName(item.user_id)}</td>
                    <td>
                      <button
                        type="button"
                        className="btn-dismiss"
                        style={{ fontWeight: 600, color: 'var(--text-primary)', textAlign: 'left', padding: 0 }}
                        onClick={() => setOpenId(openId === item.id ? null : item.id)}
                        aria-expanded={openId === item.id}
                      >
                        <i className={`fa-solid fa-chevron-${openId === item.id ? 'up' : 'down'}`} /> {item.title}
                      </button>
                      <div className="muted" style={{ fontSize: '0.8rem' }}>
                        {statusLabel(item.request_type)}
                        {item.assigned_staff_id ? ` · assigned to ${userName(item.assigned_staff_id)}` : ' · unassigned'}
                      </div>
                    </td>
                    <td>{item.priority}</td>
                    <td>
                      <StatusBadge status={item.status} />
                    </td>
                    <td>
                      <div className="quick-action-group">
                        {(REQUEST_NEXT[item.status] || []).map((next) => (
                          <button
                            key={next}
                            type="button"
                            className={`btn-icon ${ACTION[next].className}`}
                            title={ACTION[next].title}
                            aria-label={ACTION[next].title}
                            onClick={() => act(updateRequestStatus(item.id, next), `${item.request_number}: ${statusLabel(next)}`)}
                          >
                            <i className={`fa-solid ${ACTION[next].icon}`} />
                          </button>
                        ))}
                        {REQUEST_NEXT[item.status] && item.assigned_staff_id !== user.id && (
                          <button
                            type="button"
                            className="button button-sm secondary-button"
                            style={{ padding: '0.25rem 0.6rem' }}
                            onClick={() => act(assignRequest(item.id, user.id), `${item.request_number} assigned to you`)}
                          >
                            Assign to me
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {openId === item.id && (
                    <tr className="detail-row">
                      <td colSpan={6}>
                        <RequestDetail requestId={item.id} isOwner={false} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <EmptyState icon="fa-solid fa-inbox" title="No Requests Found" text="No service tickets match the selected filter." />
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
