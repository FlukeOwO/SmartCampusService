import { api } from '../api/client'

/**
 * การกระทำของเจ้าหน้าที่ที่ใช้ทั้งในหน้า Dashboard และหน้าจัดการ
 * คืน null ถ้าผู้ใช้กดยกเลิกช่องกรอกเหตุผล
 */

export function updateRequestStatus(id, status) {
  const body = { status }
  if (status === 'rejected') {
    const reason = window.prompt('Reason for rejecting this request?')
    if (!reason) return null
    body.rejection_reason = reason
  }
  if (status === 'completed') {
    const resolution = window.prompt('How was it resolved? (optional)')
    if (resolution === null) return null
    body.resolution = resolution || null
  }
  return api(`/requests/${id}/status`, { method: 'PATCH', json: body })
}

export function assignRequest(id, staffId) {
  return api(`/requests/${id}/assign`, { method: 'PATCH', json: { assigned_staff_id: staffId } })
}

export function approveBooking(id) {
  return api(`/bookings/${id}/approve`, { method: 'PUT' })
}

export function rejectBooking(id) {
  const reason = window.prompt('Reason for rejecting this booking?')
  if (!reason) return null
  return api(`/bookings/${id}/reject`, { method: 'PUT', json: { rejection_reason: reason } })
}

export function cancelBooking(id) {
  const reason = window.prompt('Reason for cancelling this booking?')
  if (!reason) return null
  return api(`/bookings/${id}/cancel`, { method: 'PUT', json: { cancellation_reason: reason } })
}

/** ปุ่มที่กดได้ตามลำดับสถานะของ backend: pending -> in_progress/rejected, in_progress -> completed/rejected */
export const REQUEST_NEXT = {
  pending: ['in_progress', 'rejected'],
  in_progress: ['completed', 'rejected'],
}
