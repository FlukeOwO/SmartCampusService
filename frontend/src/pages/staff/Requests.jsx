import { Fragment, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listAll } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { useDialog } from '../../components/Dialog'
import RequestDetail from '../../components/RequestDetail'
import { ActionButton, EmptyState, ErrorState, Loading, PageHeader, SearchBox, StatusBadge, TabPills } from '../../components/ui'
import { formatDateTime, statusLabel } from '../../lib/format'
import { REQUEST_ACTION, REQUEST_NEXT, assignRequest, updateRequestStatus } from '../../lib/staffActions'
import { useAction } from '../../lib/useAction'
import { matches } from '../../lib/search'
import { useApi } from '../../lib/useApi'
import { useUserNames } from '../../lib/useUserNames'

const TABS = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending', icon: 'fa-clock', color: '#fbbf24' },
  { value: 'in_progress', label: 'In Progress', icon: 'fa-play', color: '#0284c7' },
  { value: 'completed', label: 'Completed', icon: 'fa-check', color: '#34d399' },
  { value: 'rejected', label: 'Rejected', icon: 'fa-xmark', color: '#f87171' },
  { value: 'cancelled', label: 'Cancelled', icon: 'fa-ban', color: '#94a3b8' },
]


export default function StaffRequests() {
  const { user } = useAuth()
  const ask = useDialog()
  const userName = useUserNames()
  const [params, setParams] = useSearchParams()
  const status = params.get('status') || 'all'
  const [query, setQuery] = useState('')
  const [openId, setOpenId] = useState(null)
  const { data, error, loading, reload } = useApi(
    () => listAll('/requests', status === 'all' ? {} : { status }),
    [status],
  )

  const { run, busyKey } = useAction(reload)

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
                        className="row-toggle"
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
                          <ActionButton
                            key={next}
                            {...REQUEST_ACTION[next]}
                            label={`${REQUEST_ACTION[next].title}: ${item.request_number}`}
                            busy={busyKey === `${item.id}:${next}`}
                            disabled={busyKey !== null}
                            onClick={() => run(`${item.id}:${next}`, () => updateRequestStatus(ask, item, next), `${item.request_number}: ${statusLabel(next)}`)}
                          />
                        ))}
                        {REQUEST_NEXT[item.status] && item.assigned_staff_id !== user.id && (
                          <button
                            type="button"
                            className="button button-sm secondary-button"
                            aria-disabled={busyKey !== null || undefined}
                            onClick={() => run(`${item.id}:assign`, () => assignRequest(item.id, user.id), `${item.request_number} assigned to you`)}
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
