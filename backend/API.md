# Smart Campus API (v1)

Base URL: `/api/v1` · Swagger: `/api/v1/docs` (ปิดใน production) · Auth: `Authorization: Bearer <access_token>`

## Conventions

- **Error** ทุกชนิดตอบรูปแบบเดียว: `{"message": "...", "details": ...}`

  | Status | ใช้เมื่อ |
  |---|---|
  | 400 | กฎธุรกิจไม่ผ่าน เช่น จองย้อนหลัง, ห้องปิดซ่อม, เปลี่ยนสถานะผิดลำดับ |
  | 401 | ไม่มี token / token หมดอายุ / ใช้ refresh token แทน access token |
  | 403 | role ไม่พอ หรือไม่ใช่เจ้าของข้อมูล |
  | 404 | ไม่พบข้อมูล |
  | 409 | จองซ้อน, อีเมล/รหัสซ้ำ, ลบห้อง/อุปกรณ์ที่มีประวัติการจอง |
  | 413 | ไฟล์ใหญ่เกิน 10 MB |
  | 422 | รูปแบบข้อมูลผิด (Pydantic) |
  | 429 | login เกิน 5 ครั้ง/นาที/IP |

- **List** ทุกตัวรับ `?page=1&page_size=20` (สูงสุด 100) และตอบ `{"items": [...], "total", "page", "page_size"}`
- **เวลา** ต้องเป็น ISO 8601 ที่มี timezone เช่น `2026-10-20T09:00:00+07:00` (ไม่มี offset → 422) และระบบตอบกลับเป็น UTC
- **Role**: `student` < `staff` < `admin`

## Auth — `/auth`

| Method | Path | ใคร | หมายเหตุ |
|---|---|---|---|
| POST | `/auth/register` | สาธารณะ | ได้ role `student` เสมอ (role ที่ส่งมาถูกเพิกเฉย) |
| POST | `/auth/login` | สาธารณะ | `{email, password}` → `access_token` (30 นาที), `refresh_token` (7 วัน), `user` |
| POST | `/auth/refresh` | สาธารณะ | `{refresh_token}` → `access_token` ใหม่ |
| GET / PUT | `/auth/me` | login | ดู/แก้โปรไฟล์ |
| PUT | `/auth/me/password` | login | `{current_password, new_password}` |
| GET | `/auth/users?role=` | admin | รายชื่อผู้ใช้ |
| POST | `/auth/users` | admin | สร้างบัญชี staff/admin (`role`) |
| PATCH | `/auth/users/{id}` | admin | `{role?, is_active?}` |

## Requests (คำร้อง/แจ้งปัญหา) — `/requests`

| Method | Path | ใคร | หมายเหตุ |
|---|---|---|---|
| POST | `/requests` | login | `multipart/form-data`: `title`, `description`, `request_type`, `priority`, `location`, `contact_phone`, `files[]` (≤5 ไฟล์) |
| GET | `/requests/me?status=` | login | คำร้องของตัวเอง |
| GET | `/requests?status=&request_type=&priority=&assigned_staff_id=&search=` | staff | ทั้งหมด |
| GET | `/requests/{id}` | เจ้าของ / staff | รวม `attachments` |
| PATCH | `/requests/{id}` | เจ้าของ | แก้ได้ขณะ `pending` |
| POST | `/requests/{id}/cancel` | เจ้าของ | เฉพาะ `pending` |
| POST | `/requests/{id}/feedback` | เจ้าของ | `{rating 1-5, feedback}` หลัง `completed` |
| PATCH | `/requests/{id}/status` | staff | `pending → in_progress/rejected`, `in_progress → completed/rejected` (`rejected` ต้องมี `rejection_reason`) |
| PATCH | `/requests/{id}/assign` | staff | `{assigned_staff_id}` ต้องเป็น staff/admin ที่ active |
| POST | `/requests/{id}/attachments` | เจ้าของ | `files[]` |
| GET | `/requests/{id}/attachments/{aid}/url` | เจ้าของ / staff | `{url, expires_in_seconds}` — Signed URL อายุ 15 นาที |

ไฟล์ที่รับ: `.jpg .jpeg .png .gif .webp .pdf .docx .xlsx` ≤ 10 MB และเนื้อไฟล์ต้องตรงกับนามสกุล (ตรวจ magic bytes)

## Bookings — `/bookings`

| Method | Path | ใคร | หมายเหตุ |
|---|---|---|---|
| POST | `/bookings/rooms` | login | `{room_id, title, start_time, end_time, attendees_count?, ...}` → `pending` |
| POST | `/bookings/equipments` | login | `{equipment_id, title, start_time, end_time, ...}` |
| GET | `/bookings/me?status=` | login | การจองของตัวเอง |
| GET | `/bookings?status=&room_id=&equipment_id=&start_from=&start_to=` | staff | ทั้งหมด (เช่น `?status=pending` = คิวรออนุมัติ) |
| GET | `/bookings/rooms/{id}/availability?start_time=&end_time=` | login | `{available, busy_slots[]}` |
| GET | `/bookings/equipments/{id}/availability?start_time=&end_time=` | login | |
| GET | `/bookings/{id}` | เจ้าของ / staff | |
| PUT | `/bookings/{id}/approve` | staff | `pending → confirmed` |
| PUT | `/bookings/{id}/reject` | staff | `{rejection_reason}` |
| PUT | `/bookings/{id}/cancel` | เจ้าของ (ก่อนเริ่ม) / staff | `{cancellation_reason}` |

กฎการจอง: `start < end`, ไม่ย้อนหลัง, ยาว 15 นาที–24 ชั่วโมง (อุปกรณ์ ≤ 7 วัน), ล่วงหน้าไม่เกิน 90 วัน,
ห้อง/อุปกรณ์ต้อง `available` + `is_bookable`, `attendees_count` ≤ ความจุห้อง

**กันจองซ้อน 2 ชั้น**: (1) `SELECT ... FOR UPDATE` ล็อกแถวห้อง/อุปกรณ์แล้วตรวจช่วงเวลาที่ทับกับการจอง
`pending`/`confirmed` (2) exclusion constraint `no_overlap_room` / `no_overlap_equipment` ใน PostgreSQL —
ทั้งสองชั้นตอบ `409` · ช่วงเวลาแบบ `[start, end)` จึงจองต่อกันพอดีได้

## Inventory — `/inventory`

| Method | Path | ใคร |
|---|---|---|
| GET | `/inventory/rooms?building=&room_type=&status=&bookable=&min_capacity=&search=` | login |
| GET | `/inventory/rooms/{id}` | login |
| POST / PATCH / DELETE | `/inventory/rooms[/{id}]` | staff |
| GET | `/inventory/equipments?equipment_type=&status=&bookable=&search=` | login |
| GET | `/inventory/equipments/{id}` | login |
| POST / PATCH / DELETE | `/inventory/equipments[/{id}]` | staff |

อุปกรณ์ 1 แถว = 1 ชิ้น · ลบไม่ได้ (409) ถ้าเคยถูกจอง (กันประวัติการจองหาย) — ให้เปลี่ยน `status`/`is_bookable` แทน

## Notifications — `/notifications` (เห็นเฉพาะของตัวเอง)

| Method | Path | หมายเหตุ |
|---|---|---|
| GET | `/notifications?unread_only=` | ใหม่สุดก่อน |
| GET | `/notifications/stats/summary` | `{total, unread, read}` — Frontend poll ทุก ~30 วินาที |
| GET | `/notifications/{id}` | |
| PATCH | `/notifications/{id}/read` | |
| POST | `/notifications/read/all` | `{updated}` |
| DELETE | `/notifications/{id}` | |
| DELETE | `/notifications/read` | ลบที่อ่านแล้วทั้งหมด |

ระบบสร้าง notification อัตโนมัติใน transaction เดียวกับการเปลี่ยนสถานะ: สร้าง/อนุมัติ/ปฏิเสธ/ยกเลิกการจอง,
สร้างคำร้อง, เปลี่ยนสถานะคำร้อง, มอบหมายงาน (แจ้ง staff ที่ได้รับมอบหมาย)

## Health

| Path | ใช้ทำ |
|---|---|
| `GET /healthz` | startup/liveness probe ของ Cloud Run (ไม่แตะ DB) |
| `GET /readyz` | ตรวจ DB (`503` ถ้าต่อไม่ได้) |
