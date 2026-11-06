/** ตัวช่วยแปลงเวลาและข้อความสถานะ */

const dateTime = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
const shortDate = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
})

export function formatDateTime(value) {
  return value ? dateTime.format(new Date(value)) : ''
}

export function formatShort(value) {
  return value ? shortDate.format(new Date(value)) : ''
}

/** ค่าจาก <input type="datetime-local"> (เวลาท้องถิ่น ไม่มี timezone) -> ISO 8601 แบบ UTC ที่ API ต้องการ */
export function localInputToIso(value) {
  return new Date(value).toISOString()
}

/** Date -> ค่าสำหรับ <input type="datetime-local"> ตามเวลาท้องถิ่น */
export function toLocalInput(date) {
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

/** ช่วงเวลาเริ่มต้นของ modal จอง: ชั่วโมงถัดไป ยาว 1 ชั่วโมง */
export function defaultSlot() {
  const start = new Date()
  start.setMinutes(0, 0, 0)
  start.setHours(start.getHours() + 1)
  const end = new Date(start.getTime() + 60 * 60 * 1000)
  return { start: toLocalInput(start), end: toLocalInput(end) }
}

export function statusLabel(status) {
  return (status || '').replace(/_/g, ' ')
}

export const REQUEST_TYPES = ['maintenance', 'complaint', 'inquiry', 'other']
export const PRIORITIES = ['low', 'medium', 'high', 'urgent']
export const ROOM_TYPES = ['classroom', 'meeting_room', 'laboratory', 'auditorium', 'studio', 'other']
export const ROOM_STATUSES = ['available', 'in_use', 'maintenance', 'closed']
export const EQUIPMENT_STATUSES = ['available', 'in_use', 'maintenance', 'broken', 'retired']

export const ALLOWED_UPLOADS = '.jpg,.jpeg,.png,.gif,.webp,.pdf,.docx,.xlsx'
export const MAX_FILES = 5
export const MAX_FILE_MB = 10

/** ชั่วโมง (ทศนิยม) -> "under 1 hour" / "5 hours" / "2.5 days" */
export function formatDuration(hours) {
  if (hours < 1) return 'under 1 hour'
  if (hours < 48) {
    const h = Math.round(hours)
    return `${h} ${h === 1 ? 'hour' : 'hours'}`
  }
  return `${(hours / 24).toFixed(1)} days`
}
