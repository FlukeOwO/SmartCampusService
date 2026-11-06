import { useState } from 'react'
import { api } from '../api/client'
import { formatDateTime, statusLabel } from '../lib/format'
import { useApi } from '../lib/useApi'
import { useDialog } from './Dialog'
import { useFlash } from './Flash'
import { ErrorState, Loading } from './ui'

function formatSize(bytes) {
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(bytes / 1024)} KB`
}

/** รายละเอียดคำร้อง + ไฟล์แนบ (เปิดผ่าน Signed URL) ใช้ทั้งฝั่งนักศึกษาและเจ้าหน้าที่ */
export default function RequestDetail({ requestId, isOwner, onChanged }) {
  const flash = useFlash()
  const ask = useDialog()
  const { data: req, error, loading, reload } = useApi(() => api(`/requests/${requestId}`), [requestId])
  const [rating, setRating] = useState(5)
  const [busy, setBusy] = useState(false)

  if (loading) return <Loading text="Loading details..." />
  if (error) return <ErrorState error={error} onRetry={reload} />

  const openAttachment = async (attachment) => {
    // เปิดแท็บก่อนแล้วค่อยใส่ URL เพื่อไม่ให้ browser บล็อก popup
    const tab = window.open('', '_blank')
    try {
      const { url } = await api(`/requests/${requestId}/attachments/${attachment.id}/url`)
      if (tab) tab.location.assign(url)
      else window.location.assign(url)
    } catch (err) {
      tab?.close()
      flash(err.message, 'danger')
    }
  }

  const run = async (fn, message) => {
    setBusy(true)
    try {
      await fn()
      flash(message, 'success')
      await reload()
      onChanged?.()
    } catch (err) {
      flash(err.message, 'danger')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack">
      <div className="detail-grid">
        <div>
          <div className="muted">Request number</div>
          <strong>{req.request_number}</strong>
        </div>
        <div>
          <div className="muted">Type / Priority</div>
          <strong>
            {statusLabel(req.request_type)} · {req.priority}
          </strong>
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <div className="muted">Description</div>
          <div style={{ whiteSpace: 'pre-wrap' }}>{req.description}</div>
        </div>
        {req.contact_phone && (
          <div>
            <div className="muted">Contact phone</div>
            {req.contact_phone}
          </div>
        )}
        <div>
          <div className="muted">Assigned staff</div>
          {req.assigned_staff_id ? req.assigned_staff_name || 'A staff member' : 'Not assigned yet'}
        </div>
        {req.status_notes && (
          <div>
            <div className="muted">Staff notes</div>
            {req.status_notes}
          </div>
        )}
        {req.resolution && (
          <div>
            <div className="muted">Resolution</div>
            {req.resolution}
          </div>
        )}
        {req.rejection_reason && (
          <div>
            <div className="muted">Rejection reason</div>
            {req.rejection_reason}
          </div>
        )}
        {req.completed_at && (
          <div>
            <div className="muted">Completed</div>
            {formatDateTime(req.completed_at)}
          </div>
        )}
        {req.rating && (
          <div>
            <div className="muted">Rating</div>
            <span aria-label={`${req.rating} out of 5`}>
              {'★'.repeat(req.rating)}
              {'☆'.repeat(5 - req.rating)}
            </span>{' '}
            {req.feedback}
          </div>
        )}
      </div>

      <div>
        <div className="muted" style={{ fontSize: '0.86rem', marginBottom: '0.3rem' }}>
          Attachments ({req.attachments.length})
        </div>
        {req.attachments.length === 0 ? (
          <span className="muted" style={{ fontSize: '0.85rem' }}>
            No files attached.
          </span>
        ) : (
          <div className="attachment-list">
            {req.attachments.map((a) => (
              <button key={a.id} type="button" className="button button-sm secondary-button" onClick={() => openAttachment(a)}>
                <i className="fa-solid fa-paperclip" /> {a.filename} ({formatSize(a.file_size)})
              </button>
            ))}
          </div>
        )}
      </div>

      {isOwner && req.status === 'pending' && (
        <div>
          <button
            type="button"
            className="button button-sm danger-button"
            disabled={busy}
            onClick={async () => {
              const ok = await ask({
                title: `Cancel ${req.request_number}?`,
                message: 'Staff will stop working on it. You can submit a new request later.',
                confirmLabel: 'Cancel request',
                danger: true,
              })
              if (ok) run(() => api(`/requests/${req.id}/cancel`, { method: 'POST' }), 'Request cancelled')
            }}
          >
            <i className="fa-solid fa-ban" /> Cancel Request
          </button>
        </div>
      )}

      {isOwner && req.status === 'completed' && !req.rating && (
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <label htmlFor={`rating-${req.id}`} style={{ margin: 0 }}>
            Rate this service
          </label>
          <select id={`rating-${req.id}`} value={rating} onChange={(e) => setRating(Number(e.target.value))}>
            {[5, 4, 3, 2, 1].map((n) => (
              <option key={n} value={n}>
                {n} {n === 1 ? 'star' : 'stars'}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="button button-sm"
            disabled={busy}
            onClick={() =>
              run(() => api(`/requests/${req.id}/feedback`, { method: 'POST', json: { rating } }), 'Thank you for your feedback')
            }
          >
            Submit
          </button>
        </div>
      )}
    </div>
  )
}
