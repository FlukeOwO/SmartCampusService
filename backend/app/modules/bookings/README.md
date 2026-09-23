# Booking Service

## Overview

Booking Service จัดการการจองห้องและอุปกรณ์ โดยใช้ **Pessimistic Locking** (`SELECT FOR UPDATE`) เพื่อป้องกัน Race Condition และ Double Booking

## Features

### 1. Transaction Locking

```python
# Lock ห้องก่อนตรวจสอบความพร้อม
room_query = (
    select(Room)
    .where(Room.id == room_id)
    .with_for_update()  # Pessimistic Lock
)
```

### 2. Conflict Detection

ระบบตรวจสอบการทับซ้อนของเวลาด้วยเงื่อนไข:
- `start_time < existing_end_time`
- `end_time > existing_start_time`

### 3. Double Booking Prevention

Process:
1. **Lock** resource (room/equipment) ด้วย `SELECT FOR UPDATE`
2. **Check** availability และ conflicts
3. **Create** booking ภายใน transaction
4. **Commit** transaction

## Usage Example

```python
from app.modules.bookings import BookingService
from app.schemas.booking import BookingCreateRoom

# สร้าง service
booking_service = BookingService(db)

# สร้างการจองห้อง
booking_data = BookingCreateRoom(
    room_id=1,
    title="ประชุมกลุ่ม",
    start_time=datetime(2024, 1, 15, 9, 0),
    end_time=datetime(2024, 1, 15, 11, 0),
)

booking = await booking_service.create_room_booking(
    user_id=1,
    booking_data=booking_data
)
```

## API Endpoints

- `POST /bookings/rooms` - จองห้อง
- `POST /bookings/equipments` - จองอุปกรณ์
- `GET /bookings/{id}` - ดูรายละเอียดการจอง
- `GET /bookings/me` - ดูการจองของตัวเอง
- `PUT /bookings/{id}/approve` - อนุมัติการจอง (Staff/Admin)
- `PUT /bookings/{id}/reject` - ปฏิเสธการจอง (Staff/Admin)
- `PUT /bookings/{id}/cancel` - ยกเลิกการจอง
- `GET /rooms/{id}/availability` - ตรวจสอบความว่างของห้อง
- `GET /equipments/{id}/availability` - ตรวจสอบความว่างของอุปกรณ์

## Database Indexes

Indexes ที่เพิ่มประสิทธิภาพ:
- `ix_bookings_room_time` - สำหรับ conflict detection ห้อง
- `ix_bookings_equipment_time` - สำหรับ conflict detection อุปกรณ์
- `ix_bookings_user_status` - สำหรับ query การจองของผู้ใช้
- `ix_bookings_status_time` - สำหรับ query ตามสถานะและเวลา

## Testing Concurrent Bookings

ทดสอบการจองพร้อมกัน:

```python
import asyncio

async def test_concurrent_bookings():
    # สร้าง 2 bookings พร้อมกัน
    task1 = booking_service.create_room_booking(user1_id, booking_data)
    task2 = booking_service.create_room_booking(user2_id, booking_data)
    
    results = await asyncio.gather(task1, task2, return_exceptions=True)
    
    # หนึ่งรายการควรสำเร็จ, อีกรายการควรได้ ConflictException
    assert sum(isinstance(r, Exception) for r in results) == 1
```

## Error Handling

- `NotFoundException` - ไม่พบห้อง/อุปกรณ์
- `ValidationException` - ห้อง/อุปกรณ์ไม่พร้อมใช้งาน
- `ConflictException` - มีการจองซ้ำในช่วงเวลานั้น

## Performance Considerations

1. **Connection Pool**: ใช้ connection pool ขนาดเหมาะสม
2. **Lock Timeout**: ตั้งค่า `statement_timeout` ใน PostgreSQL
3. **Index Optimization**: ใช้ composite indexes สำหรับ query ที่ซับซ้อน
4. **Cache**: Cache ข้อมูลห้อง/อุปกรณ์ที่ไม่ค่อยเปลี่ยน

## Cloud Deployment

สำหรับ Cloud SQL (GCP):
- ใช้ `NullPool` แทน connection pooling
- ตั้งค่า `pool_pre_ping=True` เพื่อตรวจสอบ connection
- ใช้ Cloud SQL Proxy สำหรับ secure connection
