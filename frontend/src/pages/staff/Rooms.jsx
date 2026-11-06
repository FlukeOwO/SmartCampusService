import { useState } from 'react'
import { api } from '../../api/client'
import { useFlash } from '../../components/Flash'
import { EmptyState, ErrorState, Loading, PageHeader, SearchBox } from '../../components/ui'
import { ROOM_STATUSES, ROOM_TYPES, statusLabel } from '../../lib/format'
import { matches } from '../../lib/search'
import { useResources } from '../../lib/useResources'

const EMPTY = { room_number: '', room_name: '', building: '', floor: 1, capacity: 30, room_type: 'classroom' }

export default function StaffRooms() {
  const flash = useFlash()
  const { rooms, error, loading, reload } = useResources()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [query, setQuery] = useState('')

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const act = async (fn, message) => {
    try {
      await fn()
      flash(message, 'success')
      reload()
      return true
    } catch (err) {
      // 409 ตอนลบ = ห้องเคยถูกจอง (เก็บประวัติไว้) ให้เปลี่ยนสถานะแทน
      flash(err.message, 'danger')
      return false
    }
  }

  const onCreate = async (e) => {
    e.preventDefault()
    const ok = await act(
      () => api('/inventory/rooms', { method: 'POST', json: { ...form, floor: Number(form.floor), capacity: Number(form.capacity) } }),
      `Room '${form.room_number}' added successfully`,
    )
    if (ok) {
      setForm(EMPTY)
      setShowForm(false)
    }
  }

  const update = (room, patch, message) => act(() => api(`/inventory/rooms/${room.id}`, { method: 'PATCH', json: patch }), message)

  const shown = rooms.filter((r) => matches(query, r.room_number, r.room_name, r.building))

  return (
    <>
      <PageHeader icon="fa-door-closed" title="Room Management" subtitle="Configure lecture halls, study rooms, and campus spaces.">
        <button type="button" className="button" onClick={() => setShowForm(!showForm)}>
          <i className="fa-solid fa-plus-circle" /> Add New Room
        </button>
      </PageHeader>

      <div className={`expandable-panel ${showForm ? 'show' : ''}`}>
        <h3 style={{ marginBottom: '1.25rem' }}>
          <i className="fa-solid fa-plus" style={{ color: 'var(--primary)' }} /> Create New Room
        </h3>
        <form onSubmit={onCreate}>
          <div className="grid grid-3">
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="room_number">Room Code</label>
              <input id="room_number" required maxLength={50} placeholder="e.g. A101" value={form.room_number} onChange={set('room_number')} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="room_name">Room Name</label>
              <input id="room_name" required maxLength={255} placeholder="e.g. Lecture Room A101" value={form.room_name} onChange={set('room_name')} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="room_type">Type</label>
              <select id="room_type" value={form.room_type} onChange={set('room_type')}>
                {ROOM_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {statusLabel(t)}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="building">Building</label>
              <input id="building" required maxLength={100} placeholder="e.g. Building A" value={form.building} onChange={set('building')} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="floor">Floor</label>
              <input id="floor" type="number" required min={-5} max={200} value={form.floor} onChange={set('floor')} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="capacity">Capacity (Seats)</label>
              <input id="capacity" type="number" required min={1} value={form.capacity} onChange={set('capacity')} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" className="button secondary-button button-sm" onClick={() => setShowForm(false)}>
              Cancel
            </button>
            <button type="submit" className="button button-sm">
              <i className="fa-solid fa-check" /> Save Room
            </button>
          </div>
        </form>
      </div>

      <div className="toolbar-container" style={{ marginTop: 0 }}>
        <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          Total rooms configured: <strong>{rooms.length}</strong>
        </p>
        <SearchBox value={query} onChange={setQuery} placeholder="Search rooms or building..." />
      </div>

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading ? (
        <Loading />
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Room</th>
                <th>Building</th>
                <th>Capacity</th>
                <th>Status</th>
                <th>Bookable</th>
                <th style={{ width: 100 }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((room) => (
                <tr key={room.id}>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    <i className="fa-solid fa-door-open" style={{ color: 'var(--primary)', marginRight: 6 }} />
                    {room.room_number} {room.room_name}
                    <div className="muted" style={{ fontWeight: 'normal', fontSize: '0.8rem' }}>
                      {statusLabel(room.room_type)}
                    </div>
                  </td>
                  <td>
                    {room.building}, floor {room.floor}
                  </td>
                  <td>{room.capacity} seats</td>
                  <td>
                    <select
                      aria-label={`Status of ${room.room_number}`}
                      value={room.status}
                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
                      onChange={(e) => update(room, { status: e.target.value }, `${room.room_number} is now ${statusLabel(e.target.value)}`)}
                    >
                      {ROOM_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {statusLabel(s)}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`${room.room_number} bookable`}
                      checked={room.is_bookable}
                      onChange={(e) => update(room, { is_bookable: e.target.checked }, `${room.room_number} updated`)}
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="button button-sm danger-button"
                      style={{ padding: '0.25rem 0.6rem' }}
                      onClick={() =>
                        window.confirm(`Delete room ${room.room_number}?`) &&
                        act(() => api(`/inventory/rooms/${room.id}`, { method: 'DELETE' }), `Room '${room.room_number}' deleted`)
                      }
                    >
                      <i className="fa-solid fa-trash-can" /> Delete
                    </button>
                  </td>
                </tr>
              ))}
              {shown.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <EmptyState icon="fa-solid fa-door-closed" title="No Rooms Configured" text='Click "Add New Room" above to register campus spaces.' />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
