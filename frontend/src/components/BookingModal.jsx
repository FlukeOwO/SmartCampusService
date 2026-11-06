import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { localInputToIso } from '../lib/format'
import { useFlash } from './Flash'
import { Modal } from './ui'

/** ชั่วโมงเปิด-ปิดเริ่มต้น (ห้อง) — ภายหลังควรมาจากข้อมูลห้อง */
const OPEN_HOUR = 8
const CLOSE_HOUR = 20

function todayStr() {
  const d = new Date()
  return d.toISOString().slice(0, 10)
}

function pad(n) {
  return String(n).padStart(2, '0')
}

function localDateTime(dateStr, hour) {
  return `${dateStr}T${pad(hour)}:00`
}

function overlaps(busy, start, end) {
  const s = new Date(start).getTime()
  const e = new Date(end).getTime()
  return busy.some((b) => {
    const bs = new Date(b.start_time).getTime()
    const be = new Date(b.end_time).getTime()
    return s < be && e > bs
  })
}

/**
 * Modal จองห้อง/อุปกรณ์
 * - เลือกวันที่ แล้วคลิกกล่องชั่วโมง (เทา = มีคนจองแล้ว)
 * - คลิกครั้งแรก = เริ่ม, คลิกครั้งที่สอง = สิ้นสุด (ช่วงต่อเนื่อง)
 */
export default function BookingModal({ target, onClose }) {
  const flash = useFlash()
  const navigate = useNavigate()
  const path = target.kind === 'room' ? 'rooms' : 'equipments'

  const [date, setDate] = useState(todayStr)
  const [selected, setSelected] = useState([])
  const [title, setTitle] = useState(target.kind === 'room' ? 'จองห้อง' : 'ยืมอุปกรณ์')
  const [attendees, setAttendees] = useState('')
  const [busySlots, setBusySlots] = useState([])
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const hours = useMemo(() => {
    const list = []
    for (let h = OPEN_HOUR; h < CLOSE_HOUR; h++) list.push(h)
    return list
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoadingSlots(true)
    const start = localDateTime(date, OPEN_HOUR)
    const end = localDateTime(date, CLOSE_HOUR)
    api(`/bookings/${path}/${target.id}/availability`, {
      params: { start_time: localInputToIso(start), end_time: localInputToIso(end) },
    })
      .then((res) => !cancelled && setBusySlots(res.busy_slots || []))
      .catch(() => !cancelled && setBusySlots([]))
      .finally(() => !cancelled && setLoadingSlots(false))
    return () => {
      cancelled = true
    }
  }, [date, path, target.id])

  const isBusy = (hour) => {
    const start = localDateTime(date, hour)
    const end = localDateTime(date, hour + 1)
    return overlaps(busySlots, start, end)
  }

  const isPast = (hour) => {
    const now = new Date()
    const slotStart = new Date(localDateTime(date, hour))
    return slotStart <= now
  }

  const toggleHour = (hour) => {
    if (isBusy(hour) || isPast(hour)) return
    setSelected((prev) => {
      if (prev.length === 0) return [hour]
      if (prev.includes(hour)) return prev.filter((h) => h !== hour)
      const min = Math.min(...prev, hour)
      const max = Math.max(...prev, hour)
      const range = []
      for (let h = min; h <= max; h++) {
        if (isBusy(h) || isPast(h)) continue
        range.push(h)
      }
      return range
    })
    setError(null)
  }

  const sorted = [...selected].sort((a, b) => a - b)
  const startHour = sorted[0]
  const endHour = sorted.length ? sorted[sorted.length - 1] + 1 : null

  const onSubmit = async (e) => {
    e.preventDefault()
    if (!startHour || !endHour) {
      setError('กรุณาเลือกช่วงเวลา')
      return
    }
    setSubmitting(true)
    setError(null)
    const payload = {
      title,
      start_time: localInputToIso(localDateTime(date, startHour)),
      end_time: localInputToIso(localDateTime(date, endHour)),
      ...(target.kind === 'room'
        ? { room_id: target.id, attendees_count: attendees ? Number(attendees) : null }
        : { equipment_id: target.id }),
    }
    try {
      await api(`/bookings/${path}`, { method: 'POST', json: payload })
      flash('ส่งคำขอจองแล้ว รอเจ้าหน้าที่อนุมัติ', 'success')
      onClose()
      navigate('/student/bookings')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal title="จองห้อง / อุปกรณ์" icon="fa-calendar-plus" onClose={onClose}>
      <div className="booking-target">
        <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{target.label}</div>
        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 4 }}>
          เปิด {pad(OPEN_HOUR)}:00 – {pad(CLOSE_HOUR)}:00 · กล่องเทา = มีคนจองแล้ว
        </div>
      </div>

      {error && (
        <div className="alert danger" role="alert">
          <i className="fa-solid fa-circle-exclamation" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={onSubmit}>
        <div className="form-group">
          <label htmlFor="booking-date">วันที่</label>
          <input
            id="booking-date"
            type="date"
            required
            min={todayStr()}
            value={date}
            onChange={(e) => {
              setDate(e.target.value)
              setSelected([])
            }}
          />
        </div>

        <div className="form-group">
          <label>เลือกช่วงเวลา (คลิกกล่องชั่วโมง)</label>
          {loadingSlots ? (
            <div className="muted" style={{ fontSize: '0.85rem' }}>กำลังโหลดตารางว่าง...</div>
          ) : (
            <div className="hour-grid">
              {hours.map((h) => {
                const busy = isBusy(h)
                const past = isPast(h)
                const active = selected.includes(h)
                const cls = [
                  'hour-slot',
                  busy ? 'busy' : '',
                  past && !busy ? 'past' : '',
                  active ? 'selected' : '',
                ]
                  .filter(Boolean)
                  .join(' ')
                return (
                  <button
                    key={h}
                    type="button"
                    className={cls}
                    disabled={busy || past}
                    onClick={() => toggleHour(h)}
                    title={busy ? 'มีคนจองแล้ว' : past ? 'ผ่านมาแล้ว' : `${pad(h)}:00–${pad(h + 1)}:00`}
                  >
                    {pad(h)}:00
                  </button>
                )
              })}
            </div>
          )}
          {startHour != null && endHour != null && (
            <div className="free-slot" style={{ marginTop: 8 }}>
              <i className="fa-solid fa-circle-check" /> เลือกแล้ว {pad(startHour)}:00 – {pad(endHour)}:00
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="booking-title">หัวข้อ</label>
          <input id="booking-title" type="text" required maxLength={255} value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>

        {target.kind === 'room' && (
          <div className="form-group">
            <label htmlFor="booking-attendees">จำนวนผู้ใช้ (ไม่บังคับ, สูงสุด {target.capacity})</label>
            <input
              id="booking-attendees"
              type="number"
              min={1}
              max={target.capacity}
              value={attendees}
              onChange={(e) => setAttendees(e.target.value)}
            />
          </div>
        )}

        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
          <button type="submit" className="button" style={{ flex: 1 }} disabled={submitting || !startHour}>
            <i className="fa-solid fa-check" /> {submitting ? 'กำลังส่ง...' : 'ยืนยันการจอง'}
          </button>
          <button type="button" className="button secondary-button" onClick={onClose}>
            ยกเลิก
          </button>
        </div>
      </form>
    </Modal>
  )
}
