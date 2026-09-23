# Smart Campus Service Platform - API Documentation

## 🚀 Quick Start

### Access API Documentation

```
# Development
http://localhost:8000/api/v1/docs        # Swagger UI
http://localhost:8000/api/v1/redoc       # ReDoc

# Production
https://your-domain.com/api/v1/docs
```

---

## 🔐 Authentication

ระบบใช้ JWT (JSON Web Token) สำหรับการ Authentication

### Flow

1. **Register** หรือ **Login** เพื่อรับ `access_token` และ `refresh_token`
2. ใช้ `access_token` ใน Authorization Header สำหรับทุก protected endpoints
3. เมื่อ `access_token` หมดอายุ (30 นาที) ใช้ `refresh_token` เพื่อขอ token ใหม่

### Headers Format

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## 📋 API Endpoints

### Authentication (`/api/v1/auth`)

#### POST `/auth/register`
ลงทะเบียนผู้ใช้ใหม่

**Request Body:**
```json
{
  "email": "student@example.com",
  "password": "password123",
  "full_name": "นักศึกษาทดสอบ",
  "student_id": "STD2024001",
  "phone_number": "0812345678",
  "department": "Computer Science",
  "role": "student"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "email": "student@example.com",
  "full_name": "นักศึกษาทดสอบ",
  "role": "student",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### POST `/auth/login`
เข้าสู่ระบบ

**Request Body:**
```json
{
  "email": "student@example.com",
  "password": "password123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "student@example.com",
    "full_name": "นักศึกษาทดสอบ",
    "role": "student"
  }
}
```

#### POST `/auth/refresh`
ขอ Access Token ใหม่

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### GET `/auth/me`
ดูข้อมูลโปรไฟล์ของตัวเอง

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "student@example.com",
  "full_name": "นักศึกษาทดสอบ",
  "student_id": "STD2024001",
  "role": "student",
  "department": "Computer Science",
  "phone_number": "0812345678"
}
```

---

### Bookings (`/api/v1/bookings`)

#### POST `/bookings/rooms`
จองห้อง

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "room_id": 1,
  "title": "ประชุมกลุ่มโปรเจค",
  "description": "ประชุมทำโปรเจควิชา Software Engineering",
  "purpose": "Group Study",
  "start_time": "2024-01-15T09:00:00Z",
  "end_time": "2024-01-15T11:00:00Z",
  "attendees_count": 5,
  "contact_person": "นักศึกษาทดสอบ",
  "contact_phone": "0812345678"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 1,
  "room_id": 1,
  "title": "ประชุมกลุ่มโปรเจค",
  "status": "pending",
  "start_time": "2024-01-15T09:00:00Z",
  "end_time": "2024-01-15T11:00:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Error Responses:**
- `400` - Validation error (เช่น end_time <= start_time)
- `404` - Room not found
- `409` - Conflict (ห้องถูกจองแล้วในช่วงเวลานั้น)

#### POST `/bookings/equipments`
จองอุปกรณ์

#### GET `/bookings/me`
ดูรายการการจองของตัวเอง

**Query Parameters:**
- `status`: กรองตามสถานะ (pending, confirmed, cancelled, etc.)
- `limit`: จำนวนรายการสูงสุด (default: 50)
- `offset`: เริ่มต้นจากรายการที่ (default: 0)

#### GET `/bookings/{booking_id}`
ดูรายละเอียดการจอง

#### PUT `/bookings/{booking_id}/approve`
อนุมัติการจอง (Staff/Admin only)

**Headers:** `Authorization: Bearer <token>` (Staff/Admin)

**Request Body:**
```json
{
  "notes": "อนุมัติแล้ว"
}
```

#### PUT `/bookings/{booking_id}/reject`
ปฏิเสธการจอง (Staff/Admin only)

**Request Body:**
```json
{
  "rejection_reason": "ห้องไม่พร้อมใช้งานในวันดังกล่าว"
}
```

#### PUT `/bookings/{booking_id}/cancel`
ยกเลิกการจอง (เจ้าของการจอง)

**Request Body:**
```json
{
  "cancellation_reason": "เปลี่ยนแผนการประชุม"
}
```

#### GET `/bookings/rooms/{room_id}/availability`
ตรวจสอบความว่างของห้อง

**Query Parameters:**
- `start_time`: เวลาเริ่มต้น (ISO 8601 format)
- `end_time`: เวลาสิ้นสุด (ISO 8601 format)

**Example:**
```
GET /api/v1/bookings/rooms/1/availability?start_time=2024-01-15T09:00:00Z&end_time=2024-01-15T11:00:00Z
```

**Response:**
```json
{
  "available": true,
  "room_id": 1,
  "time_slot": {
    "start_time": "2024-01-15T09:00:00Z",
    "end_time": "2024-01-15T11:00:00Z"
  }
}
```

#### GET `/bookings/equipments/{equipment_id}/availability`
ตรวจสอบความว่างของอุปกรณ์

---

### Inventory (`/api/v1/inventory`)

#### GET `/inventory/rooms`
ดูรายการห้องทั้งหมด

**Query Parameters:**
- `building`: ชื่ออาคาร
- `room_type`: ประเภทห้อง (classroom, meeting_room, laboratory, etc.)
- `status`: สถานะ (available, in_use, maintenance, closed)
- `is_bookable`: สามารถจองได้หรือไม่ (true/false)
- `limit`: จำนวนรายการสูงสุด
- `offset`: เริ่มต้นจากรายการที่

**Example:**
```
GET /api/v1/inventory/rooms?building=อาคาร A&room_type=classroom&is_bookable=true
```

#### GET `/inventory/rooms/{room_id}`
ดูรายละเอียดห้อง

**Response:**
```json
{
  "id": 1,
  "room_number": "A101",
  "room_name": "ห้องเรียนมาตรฐาน A101",
  "room_type": "classroom",
  "building": "อาคาร A",
  "floor": 1,
  "capacity": 40,
  "description": "ห้องเรียนขนาดกลาง มีเครื่องฉายโปรเจคเตอร์",
  "facilities": ["Projector", "Whiteboard", "Air Conditioner", "WiFi"],
  "status": "available",
  "is_bookable": true
}
```

#### GET `/inventory/equipments`
ดูรายการอุปกรณ์ทั้งหมด

**Query Parameters:**
- `equipment_type`: ประเภทอุปกรณ์
- `status`: สถานะ (available, in_use, maintenance, broken, retired)
- `is_bookable`: สามารถจองได้หรือไม่
- `limit`: จำนวนรายการสูงสุด
- `offset`: เริ่มต้นจากรายการที่

#### GET `/inventory/equipments/{equipment_id}`
ดูรายละเอียดอุปกรณ์

---

## 🔑 Role-Based Access Control (RBAC)

### Roles

- **student**: นักศึกษา - สามารถจองห้องและอุปกรณ์
- **staff**: เจ้าหน้าที่ - สามารถอนุมัติ/ปฏิเสธการจอง
- **admin**: ผู้ดูแลระบบ - สิทธิ์เต็ม

### Permission Matrix

| Endpoint | Student | Staff | Admin |
|----------|---------|-------|-------|
| Register/Login | ✅ | ✅ | ✅ |
| View Rooms/Equipments | ✅ | ✅ | ✅ |
| Create Booking | ✅ | ✅ | ✅ |
| View Own Bookings | ✅ | ✅ | ✅ |
| View All Bookings | ❌ | ✅ | ✅ |
| Approve/Reject | ❌ | ✅ | ✅ |
| Cancel Own Booking | ✅ | ✅ | ✅ |
| Manage Inventory | ❌ | ❌ | ✅ |

---

## 📊 Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 204 | No Content - Success with no response body |
| 400 | Bad Request - Invalid request data |
| 401 | Unauthorized - Missing or invalid token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 409 | Conflict - Resource conflict (e.g., double booking) |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error |

---

## 🧪 Testing with cURL

### Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User",
    "role": "student"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

### Create Booking (with token)
```bash
curl -X POST http://localhost:8000/api/v1/bookings/rooms \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": 1,
    "title": "Meeting",
    "start_time": "2024-01-15T09:00:00Z",
    "end_time": "2024-01-15T11:00:00Z"
  }'
```

---

## 🔒 Security Best Practices

1. ✅ ใช้ HTTPS ใน Production
2. ✅ เก็บ tokens อย่างปลอดภัย (ไม่ใช่ localStorage)
3. ✅ ตรวจสอบ token expiration
4. ✅ ใช้ refresh token สำหรับ long-lived sessions
5. ✅ Implement rate limiting (60 requests/minute)
6. ✅ Validate input data
7. ✅ Handle errors properly

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [JWT.io](https://jwt.io)
- [HTTP Status Codes](https://httpstatuses.com)
