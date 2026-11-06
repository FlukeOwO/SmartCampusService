import { useMemo } from 'react'
import { listAll } from '../api/client'
import { useApi } from './useApi'

/** โหลดห้องและอุปกรณ์ทั้งหมดไว้แปลง room_id / equipment_id เป็นชื่อที่อ่านได้ */
export function useResources() {
  const { data, error, loading, reload } = useApi(async () => {
    const [rooms, equipments] = await Promise.all([
      listAll('/inventory/rooms'),
      listAll('/inventory/equipments'),
    ])
    return { rooms, equipments }
  }, [])

  const lookup = useMemo(() => {
    const rooms = new Map((data?.rooms || []).map((r) => [r.id, r]))
    const equipments = new Map((data?.equipments || []).map((e) => [e.id, e]))
    return { rooms, equipments }
  }, [data])

  return { rooms: data?.rooms || [], equipments: data?.equipments || [], lookup, error, loading, reload }
}

/** ข้อมูลแสดงผลของสิ่งที่ถูกจองใน booking หนึ่งรายการ */
export function describeBooking(booking, lookup) {
  if (booking.room_id) {
    const room = lookup.rooms.get(booking.room_id)
    return {
      kind: 'Room',
      icon: 'fa-door-open',
      name: room ? `${room.room_number} ${room.room_name}` : `Room #${booking.room_id}`,
      meta: room?.building || '',
    }
  }
  const item = lookup.equipments.get(booking.equipment_id)
  return {
    kind: 'Equipment',
    icon: 'fa-laptop',
    name: item ? item.equipment_name : `Equipment #${booking.equipment_id}`,
    meta: item?.equipment_type || '',
  }
}
