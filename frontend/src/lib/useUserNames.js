import { useMemo } from 'react'
import { listAll } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useApi } from './useApi'

/** ชื่อผู้ใช้ตาม id (API รายชื่อผู้ใช้เปิดให้เฉพาะ admin; staff จะเห็นเป็น User #id) */
export function useUserNames() {
  const { isAdmin } = useAuth()
  const { data } = useApi(() => (isAdmin ? listAll('/auth/users') : Promise.resolve([])), [isAdmin])
  return useMemo(() => {
    const users = new Map((data || []).map((u) => [u.id, u]))
    return (id) => users.get(id)?.full_name || `User #${id}`
  }, [data])
}
