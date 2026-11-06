import { useCallback, useRef, useState } from 'react'
import { useFlash } from '../components/Flash'
import { CANCELLED } from './staffActions'

/**
 * รันการกระทำทีละอย่าง (กันกดซ้ำ) แล้วแจ้งผลด้วย flash
 * busyKey บอกว่าแถวไหนกำลังทำงาน เพื่อปิดปุ่มของแถวนั้นระหว่างรอ
 */
export function useAction(onDone) {
  const flash = useFlash()
  const running = useRef(false)
  const [busyKey, setBusyKey] = useState(null)

  const run = useCallback(
    async (key, fn, message) => {
      if (running.current) return
      running.current = true
      setBusyKey(key)
      try {
        const result = await fn()
        if (result === CANCELLED) return
        if (message) flash(message, 'success')
        await onDone?.()
      } catch (err) {
        flash(err.message, 'danger')
      } finally {
        running.current = false
        setBusyKey(null)
      }
    },
    [flash, onDone],
  )

  return { run, busyKey }
}
