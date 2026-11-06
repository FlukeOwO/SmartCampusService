import { Fragment, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listAll } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { useDialog } from '../../components/Dialog'
import RequestDetail from '../../components/RequestDetail'
import { ActionButton, Drawer, EmptyState, ErrorState, Loading, PageHeader, SearchBox, StatusBadge, TabPills } from '../../components/ui'
import { formatDateTime, statusLabel } from '../../lib/format'
import { REQUEST_ACTION, REQUEST_NEXT, assignRequest, updateRequestStatus } from '../../lib/staffActions'
import { useAction } from '../../lib/useAction'
import { matches } from '../../lib/search'
import { useApi } from '../../lib/useApi'
import { useUserNames } from '../../lib/useUserNames'

const PRIORITY_CLASS = {
  high: 'priority-high',
  medium: 'priority-medium',
  low: 'priority-low',
}

function PriorityBadge({ value }) {
  const key = (value || '').toLowerCase()
  return <span className={`priority-badge ${PRIORITY_CLASS[key] || ''}`}>{statusLabel(value) || '—'}</span>
}

export default function StaffRequests() {
  const { user } = useAuth()
  const ask = useDialog()
  const userName = useUserNames()
  const [params, setParams] = useSearchParams()
  const status = params.get('status') || 'all'
  const [query, setQuery] = useState('')
  const [openId, setOpenId] = useState(null)

  // ดึงทั้งหมดเพื่อคำนวณจำนวนในแท็บ
  const { data, error, loading, reload } = useApi(() => listAll('/requests', {}), [])

  const { run, busyKey } = useAction(reload)

  const all = data || []
  const counts = useMemo(() => {
    const c = { all: all.length, pending: 0, in_progress: 0, completed: 0, rejected: 0, cancelled: 0 }
    all.forEach((r) => {
      if (c[r.status] !== undefined) c[r.status] += 1
    })
    return c
  }, [all])

  const TABS = [
    { value: 'all', label: `ทั้งหมด (${counts.all})` },
    { value: 'pending', label: `รอดำเนินการ (${counts.pending})`, icon: 'fa-clock' },
    { value: 'in_progress', label: `กำลังดำเนินการ (${counts.in_progress})`, icon: 'fa-play' },
    { value: 'completed', label: `เสร็จสิ้น (${counts.completed})`, icon: 'fa-check' },
    { value: 'rejected', label: `ปฏิเสธ (${counts.rejected})`, icon: 'fa-xmark' },
    { value: 'cancelled', label: `ยกเลิก (${counts.cancelled})`, icon: 'fa-ban' },
  ]

  const filtered = all.filter((r) => status === 'all' || r.status === status)
  const rows = filtered.filter((r) => matches(query, r.title, r.request_number, r.request_type, userName(r.user_id)))

  return (
    <>
      <PageHeader icon="fa-list-check" title="จัดการคำร้อง" subtitle="ค้นหา กรอง มอบหมาย และอัปเดตสถานะคำร้องได้ในหน้าเดียว" />

      <div className="toolbar-container">
        <TabPills tabs={TABS} active={status} onChange={(value) => setParams(value === 'all' ? {} : { status: value })} />
        <SearchBox value={query} onChange={setQuery} placeholder="ค้นหาเลขคำร้อง, หัวข้อ, ผู้แจ้ง..." />
      </div>

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading ? (
        <Loading />
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th style={{ width: 130 }}>เลขคำร้อง</th>
                <th style={{ width: 140 }}>ผู้แจ้ง</th>
                <th>หัวข้อ</th>
                <th style={{ width: 100 }}>ความสำคัญ</th>
                <th style={{ width: 130 }}>ผู้รับผิดชอบ</th>
                <th style={{ width: 120 }}>สถานะ</th>
                <th style={{ width: 160 }}>จัดการ</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => (
                <Fragment key={item.id}>
                  <tr>
                    <td>
                      <strong style={{ whiteSpace: 'nowrap' }}>{item.request_number}</strong>
                      <div className="muted" style={{ fontSize: '0.75rem' }}>
                        {formatDateTime(item.created_at)}
                      </div>
                    </td>
                    <td style={{ fontWeight: 600 }}>{userName(item.user_id)}</td>
                    <td>
                      <button
                        type="button"
                        className="row-toggle"
                        onClick={() => setOpenId(item.id)}
                        aria-expanded={openId === item.id}
                      >
                        <i className={`fa-solid fa-chevron-${openId === item.id ? 'up' : 'down'}`} /> {item.title}
                      </button>
                      <div className="muted" style={{ fontSize: '0.78rem' }}>
                        {statusLabel(item.request_type)}
                      </div>
                    </td>
                    <td>
                      <PriorityBadge value={item.priority} />
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>
                      {item.assigned_staff_id ? userName(item.assigned_staff_id) : <span className="muted">ยังไม่มอบหมาย</span>}
                    </td>
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
                            รับงาน
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>

                </Fragment>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={7}>
                    <EmptyState icon="fa-solid fa-inbox" title="ไม่พบคำร้อง" text="ไม่มีรายการที่ตรงกับตัวกรองที่เลือก" />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {openId && (
        <Drawer title="รายละเอียดคำร้อง" onClose={() => setOpenId(null)} wide>
          <RequestDetail requestId={openId} isOwner={false} onChanged={reload} />
        </Drawer>
      )}
    </>
  )
}
