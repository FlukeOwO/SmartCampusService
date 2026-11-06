import { Fragment, useState } from 'react'
import { Link } from 'react-router-dom'
import { listAll } from '../../api/client'
import RequestDetail from '../../components/RequestDetail'
import { EmptyState, ErrorState, Loading, PageHeader, SearchBox, StatusBadge, TabPills } from '../../components/ui'
import { formatDateTime, statusLabel } from '../../lib/format'
import { matches } from '../../lib/search'
import { useApi } from '../../lib/useApi'

const TABS = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending', icon: 'fa-clock', color: '#fbbf24' },
  { value: 'in_progress', label: 'In Progress', icon: 'fa-play', color: '#0284c7' },
  { value: 'completed', label: 'Completed', icon: 'fa-check', color: '#34d399' },
  { value: 'rejected', label: 'Rejected', icon: 'fa-xmark', color: '#f87171' },
]

export default function MyRequests() {
  const [tab, setTab] = useState('all')
  const [query, setQuery] = useState('')
  const [openId, setOpenId] = useState(null)
  const { data, error, loading, reload } = useApi(() => listAll('/requests/me'), [])

  const rows = (data || []).filter(
    (r) => (tab === 'all' || r.status === tab) && matches(query, r.title, r.request_number, r.request_type),
  )

  return (
    <>
      <PageHeader icon="fa-bullhorn" title="My Campus Requests" subtitle="Track tickets and issues you've reported across campus facilities.">
        <Link className="button" to="/student/requests/new">
          <i className="fa-solid fa-circle-plus" /> Report New Issue
        </Link>
      </PageHeader>

      <div className="toolbar-container">
        <TabPills tabs={TABS.map((t) => (t.value === 'all' ? { ...t, label: `All (${data?.length ?? 0})` } : t))} active={tab} onChange={setTab} />
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
                <th>Issue Details</th>
                <th>Type</th>
                <th>Status</th>
                <th>Submitted</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => (
                <Fragment key={item.id}>
                  <tr className="clickable" onClick={() => setOpenId(openId === item.id ? null : item.id)}>
                    <td>
                      <strong>{item.request_number}</strong>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="row-toggle"
                        aria-expanded={openId === item.id}
                        onClick={(e) => {
                          e.stopPropagation()
                          setOpenId(openId === item.id ? null : item.id)
                        }}
                      >
                        <i className={`fa-solid fa-chevron-${openId === item.id ? 'up' : 'down'}`} /> {item.title}
                      </button>
                    </td>
                    <td>{statusLabel(item.request_type)}</td>
                    <td>
                      <StatusBadge status={item.status} />
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
                      {formatDateTime(item.created_at)}
                    </td>
                  </tr>
                  {openId === item.id && (
                    <tr className="detail-row">
                      <td colSpan={5}>
                        <RequestDetail requestId={item.id} isOwner onChanged={reload} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <EmptyState title="No requests found" text="You haven't submitted any service tickets that match." />
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
