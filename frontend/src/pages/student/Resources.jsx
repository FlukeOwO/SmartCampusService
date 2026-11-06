import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import BookingModal from '../../components/BookingModal'
import { EmptyState, ErrorState, Loading, PageHeader, SearchBox, StatusBadge, TabPills } from '../../components/ui'
import { statusLabel } from '../../lib/format'
import { matches } from '../../lib/search'
import { useResources } from '../../lib/useResources'

const bookable = (item) => item.is_bookable && item.status === 'available'

export default function Resources() {
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') === 'equipment' ? 'equipment' : 'rooms'
  const [query, setQuery] = useState('')
  const [target, setTarget] = useState(null)
  const { rooms, equipments, error, loading, reload } = useResources()

  const shownRooms = rooms.filter(bookable).filter((r) => matches(query, r.room_number, r.room_name, r.building, r.room_type))
  const shownEquipment = equipments
    .filter(bookable)
    .filter((e) => matches(query, e.equipment_name, e.equipment_code, e.equipment_type, e.description))

  return (
    <>
      <PageHeader icon="fa-calendar-plus" title="จองทรัพยากร" subtitle="เลือกห้องเรียนหรืออุปกรณ์ที่ต้องการใช้งาน">
        <Link to="/student/bookings" className="button secondary-button">
          <i className="fa-solid fa-clock-rotate-left" /> ประวัติการจอง
        </Link>
      </PageHeader>

      <div className="toolbar-container">
        <TabPills
          active={tab}
          onChange={(value) => setParams({ tab: value })}
          tabs={[
            { value: 'rooms', label: `ห้อง (${shownRooms.length})`, icon: 'fa-door-open' },
            { value: 'equipment', label: `อุปกรณ์ (${shownEquipment.length})`, icon: 'fa-laptop' },
          ]}
        />
        <SearchBox value={query} onChange={setQuery} placeholder="ค้นหาห้องหรืออุปกรณ์..." />
      </div>

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading && <Loading />}

      {!loading && tab === 'rooms' &&
        (shownRooms.length ? (
          <div className="resource-grid">
            {shownRooms.map((room) => (
              <div key={room.id} className="resource-card">
                <div>
                  <div className="resource-header">
                    <div className="resource-title">
                      <i className="fa-solid fa-chalkboard-user" style={{ color: 'var(--primary)' }} /> {room.room_number} {room.room_name}
                    </div>
                    <StatusBadge status={room.status} />
                  </div>
                  <div className="resource-meta">
                    <span>
                      <i className="fa-solid fa-building muted" style={{ width: 16 }} /> {room.building}, floor {room.floor}
                    </span>
                    <span>
                      <i className="fa-solid fa-users muted" style={{ width: 16 }} /> Capacity: {room.capacity} seats
                    </span>
                    <span>
                      <i className="fa-solid fa-tag muted" style={{ width: 16 }} /> {statusLabel(room.room_type)}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  className="button button-block button-sm"
                  onClick={() =>
                    setTarget({
                      kind: 'room',
                      id: room.id,
                      capacity: room.capacity,
                      label: `${room.room_number} ${room.room_name} (${room.building})`,
                    })
                  }
                >
                  <i className="fa-solid fa-calendar-check" /> Book Room
                </button>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState icon="fa-solid fa-door-closed" title="No Available Rooms" text="There are currently no rooms available for reservation." />
        ))}

      {!loading && tab === 'equipment' &&
        (shownEquipment.length ? (
          <div className="resource-grid">
            {shownEquipment.map((item) => (
              <div key={item.id} className="resource-card">
                <div>
                  <div className="resource-header">
                    <div className="resource-title">
                      <i className="fa-solid fa-cube" style={{ color: 'var(--primary)' }} /> {item.equipment_name}
                    </div>
                    <StatusBadge status={item.status} />
                  </div>
                  <div className="resource-meta">
                    <span>
                      <i className="fa-solid fa-tags muted" style={{ width: 16 }} /> {item.equipment_type} · {item.equipment_code}
                    </span>
                    <span>
                      <i className="fa-solid fa-circle-info muted" style={{ width: 16 }} /> {item.description || 'No description'}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  className="button button-block button-sm"
                  onClick={() => setTarget({ kind: 'equipment', id: item.id, label: `${item.equipment_name} (${item.equipment_type})` })}
                >
                  <i className="fa-solid fa-calendar-check" /> Book Equipment
                </button>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState icon="fa-solid fa-box-open" title="No Available Equipment" text="There is currently no equipment available for checkout." />
        ))}

      {target && <BookingModal target={target} onClose={() => setTarget(null)} />}
    </>
  )
}
