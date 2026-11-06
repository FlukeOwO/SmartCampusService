/** กรองแถวด้วยข้อความค้นหาแบบเดียวกับ filterTable() เดิม */
export function matches(query, ...fields) {
  if (!query) return true
  const q = query.toLowerCase()
  return fields.some((f) => String(f ?? '').toLowerCase().includes(q))
}
