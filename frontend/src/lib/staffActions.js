import { api } from '../api/client'

/**
 * การกระทำกับคำร้องและการจอง ใช้ทั้งหน้า Dashboard และหน้าจัดการ
 * `ask` มาจาก useDialog(): ถามเหตุผลในกล่องของแอปแทน window.prompt
 * คืน CANCELLED ถ้าผู้ใช้กดย้อนกลับ
 */
export const CANCELLED = Symbol('cancelled')

export async function updateRequestStatus(ask, request, status) {
  const body = { status }
  if (status === 'rejected') {
    const reason = await ask({
      title: `Reject ${request.request_number}`,
      message: request.title,
      input: 'Reason (shown to the requester)',
      required: true,
      confirmLabel: 'Reject request',
      danger: true,
    })
    if (reason === null) return CANCELLED
    body.rejection_reason = reason
  }
  if (status === 'completed') {
    const resolution = await ask({
      title: `Complete ${request.request_number}`,
      message: request.title,
      input: 'How was it resolved? (optional)',
      confirmLabel: 'Mark completed',
    })
    if (resolution === null) return CANCELLED
    body.resolution = resolution || null
  }
  return api(`/requests/${request.id}/status`, { method: 'PATCH', json: body })
}

export function assignRequest(id, staffId) {
  return api(`/requests/${id}/assign`, { method: 'PATCH', json: { assigned_staff_id: staffId } })
}

export function approveBooking(id) {
  return api(`/bookings/${id}/approve`, { method: 'PUT' })
}

export async function rejectBooking(ask, booking) {
  const reason = await ask({
    title: `Reject booking #${booking.id}`,
    message: booking.title,
    input: 'Reason (shown to the person who booked)',
    required: true,
    confirmLabel: 'Reject booking',
    danger: true,
  })
  if (reason === null) return CANCELLED
  return api(`/bookings/${booking.id}/reject`, { method: 'PUT', json: { rejection_reason: reason } })
}

/** ใช้ได้ทั้งเจ้าของการจองและเจ้าหน้าที่ */
export async function cancelBooking(ask, booking) {
  const reason = await ask({
    title: `Cancel booking #${booking.id}`,
    message: booking.title,
    input: 'Reason for cancelling',
    required: true,
    confirmLabel: 'Cancel booking',
    danger: true,
  })
  if (reason === null) return CANCELLED
  return api(`/bookings/${booking.id}/cancel`, { method: 'PUT', json: { cancellation_reason: reason } })
}

/** ปุ่มที่กดได้ตามลำดับสถานะของ backend: pending -> in_progress/rejected, in_progress -> completed/rejected */
export const REQUEST_NEXT = {
  pending: ['in_progress', 'rejected'],
  in_progress: ['completed', 'rejected'],
}

/** ไอคอนของแต่ละการกระทำ: "เริ่มดำเนินการ" ใช้ไอคอน play ไม่ใช่ spinner ที่ดูเหมือนกำลังโหลด */
export const REQUEST_ACTION = {
  in_progress: { icon: 'fa-play', className: 'btn-progress', title: 'Start work' },
  completed: { icon: 'fa-check', className: 'btn-approve', title: 'Mark completed' },
  rejected: { icon: 'fa-xmark', className: 'btn-reject', title: 'Reject request' },
}
