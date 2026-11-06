import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { defaultSlot, formatShort, localInputToIso } from '../lib/format'
import { useFlash } from './Flash'
import { Modal } from './ui'

/**
 * Modal จองห้อง/อุปกรณ์ ใช้ร่วมกันสองแบบเหมือนของเดิม
 * ตรวจช่วงเวลาว่างกับ API ทุกครั้งที่เปลี่ยนเวลา และแปลงเวลาท้องถิ่นเป็น ISO มี timezone ก่อนส่ง
 */
export default function BookingModal({ target, onClose }) {
  const flash = useFlash()
  const navigate = useNavigate()
  const slot = defaultSlot()
  const [form, setForm] = useState({
    title: target.kind === 'room' ? 'Room reservation' : 'Equipment checkout',
    start: slot.start,
    end: slot.end,
    attendees_count: '',
    purpose: '',
  })
  const [availability, setAvailability] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const path = target.kind === 'room' ? 'rooms' : 'equipments'

  const validRange = Boolean(form.start && form.end && new Date(form.end) > new Date(form.start))

  useEffect(() => {
    if (!validRange) return undefined
    let cancelled = false
    const timer = setTimeout(() => {
      api(`/bookings/${path}/${target.id}/availability`, {
        params: { start_time: localInputToIso(form.start), end_time: localInputToIso(form.end) },
      })
        .then((result) => !cancelled && setAvailability(result))
        .catch(() => !cancelled && setAvailability(null))
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [validRange, form.start, form.end, path, target.id])

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const onSubmit = async (e) => {
    e.preventDefault()
    if (new Date(form.end) <= new Date(form.start)) {
      setError('End time must be after start time')
      return
    }
    setSubmitting(true)
    setError(null)
    const payload = {
      title: form.title,
      purpose: form.purpose || null,
      start_time: localInputToIso(form.start),
      end_time: localInputToIso(form.end),
      ...(target.kind === 'room'
        ? { room_id: target.id, attendees_count: form.attendees_count ? Number(form.attendees_count) : null }
        : { equipment_id: target.id }),
    }
    try {
      await api(`/bookings/${path}`, { method: 'POST', json: payload })
      flash('Booking reservation submitted! Waiting for staff approval.', 'success')
      onClose()
      navigate('/student/bookings')
    } catch (err) {
      // 409 = ถูกจองช่วงนี้แล้ว, 400 = กฎการจองไม่ผ่าน (ย้อนหลัง, สั้น/ยาวเกิน, เกินความจุ)
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal title="Make Reservation" icon="fa-calendar-plus" onClose={onClose}>
      <div
        style={{
          background: '#f8fafc',
          padding: '0.85rem',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--border-card)',
          marginBottom: '1.25rem',
        }}
      >
        <small className="muted" style={{ textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em', fontSize: '0.72rem' }}>
          Selected Resource
        </small>
        <div style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-primary)', marginTop: '0.2rem' }}>{target.label}</div>
      </div>

      {error && (
        <div className="alert danger" role="alert">
          <i className="fa-solid fa-circle-exclamation" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={onSubmit}>
        <div className="form-group">
          <label htmlFor="booking-title">Title</label>
          <input id="booking-title" type="text" required maxLength={255} value={form.title} onChange={set('title')} />
        </div>
        <div className="form-group">
          <label htmlFor="booking-start">
            <i className="fa-regular fa-clock" /> Start Date &amp; Time
          </label>
          <input id="booking-start" type="datetime-local" required value={form.start} onChange={set('start')} />
        </div>
        <div className="form-group">
          <label htmlFor="booking-end">
            <i className="fa-regular fa-clock" /> End Date &amp; Time
          </label>
          <input id="booking-end" type="datetime-local" required value={form.end} onChange={set('end')} />
        </div>
        {target.kind === 'room' && (
          <div className="form-group">
            <label htmlFor="booking-attendees">Attendees (optional, max {target.capacity})</label>
            <input
              id="booking-attendees"
              type="number"
              min={1}
              max={target.capacity}
              value={form.attendees_count}
              onChange={set('attendees_count')}
            />
          </div>
        )}

        {validRange && availability &&
          (availability.available ? (
            <div className="free-slot">
              <i className="fa-solid fa-circle-check" /> Available for this time slot
            </div>
          ) : (
            <div className="busy-slot">
              <i className="fa-solid fa-circle-xmark" /> Not available:{' '}
              {availability.busy_slots.length
                ? availability.busy_slots.map((s) => `${formatShort(s.start_time)}–${formatShort(s.end_time)}`).join(', ')
                : 'resource is not bookable'}
            </div>
          ))}

        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
          <button type="submit" className="button" style={{ flex: 1 }} disabled={submitting}>
            <i className="fa-solid fa-check" /> {submitting ? 'Submitting...' : 'Confirm Reservation'}
          </button>
          <button type="button" className="button secondary-button" onClick={onClose}>
            Cancel
          </button>
        </div>
      </form>
    </Modal>
  )
}
