# Smart Campus — Frontend (React + Vite)

หน้าบ้านของระบบ เรียกข้อมูลทั้งหมดจาก Backend API (FastAPI)
ดีไซน์, CSS และ page flow มาจากงานต้นแบบของทีม (`src/styles/style.css`) แล้วย้ายเป็น React

## รันบนเครื่อง

ต้องมี Node 22 (หรือ 20.19 ขึ้นไป) และ backend ที่รันอยู่ (`docker compose up -d db backend` ที่โฟลเดอร์หลัก)

```bash
npm install
npm run dev      # http://localhost:5173
npm run lint     # oxlint
npm run build    # ไฟล์ static ใน dist/
```

บัญชีทดลอง (จาก `seed.py` เมื่อ `SEED_DEMO_DATA=true`): `student1@smartcampus.dev` / `student12345`,
`staff@smartcampus.dev` / `staff12345` · บัญชี admin สร้างด้วย `SEED_ADMIN_EMAIL` + `SEED_ADMIN_PASSWORD`

## โครงสร้าง

```
src/
├── api/client.js          # เรียก API: แนบ JWT, refresh token อัตโนมัติ, แปลง error เป็น ApiError
├── auth/                  # AuthContext (login/logout/register, user ปัจจุบัน), roles
├── components/
│   ├── Layout.jsx         # navbar ตาม role + กระดิ่งแจ้งเตือน (poll ทุก 30 วินาที)
│   ├── Flash.jsx          # ข้อความแจ้งผลด้านบนหน้า (แทน flash ของ Flask)
│   ├── ui.jsx             # StatusBadge, Loading, EmptyState, ErrorState, Modal, TabPills ...
│   ├── BookingModal.jsx   # จองห้อง/อุปกรณ์ + ตรวจช่วงเวลาว่าง
│   └── RequestDetail.jsx  # รายละเอียดคำร้อง + เปิดไฟล์แนบผ่าน Signed URL
├── lib/                   # format เวลา, useApi (loading/error/reload), lookup ชื่อห้อง/อุปกรณ์
├── pages/
│   ├── Login.jsx, Register.jsx, Notifications.jsx
│   ├── student/           # Dashboard, MyRequests, CreateRequest, Resources, BookingHistory
│   └── staff/             # Dashboard, Requests, Bookings, Rooms, Equipment, Users (admin)
└── styles/
    ├── style.css          # ธีมเดิมของทีม (ไม่แก้)
    └── app.css            # ส่วนเสริม: สถานะใหม่, layout responsive, กระดิ่ง
```

## กติกาที่ต้องทำตาม (เพื่อให้ขึ้น cloud ได้โดยไม่แก้โค้ด)

| เรื่อง | ทำแบบนี้ |
|---|---|
| URL ของ API | ผ่าน `api()` ใน `src/api/client.js` เท่านั้น (อ่าน `VITE_API_BASE_URL`) ห้ามเขียน localhost ตายตัว |
| Router | `HashRouter` (`/#/student`) เพราะบน cloud โฮสต์บน Cloud Storage ที่ `https://<bucket>.storage.googleapis.com/index.html` (`base=/`) |
| เวลา | ค่าจาก `<input type="datetime-local">` แปลงด้วย `localInputToIso()` ก่อนส่ง (API ต้องมี timezone) |
| สิทธิ์ | ซ่อน/แสดงเมนูตาม `user.role` (`student` / `staff` / `admin`) แต่ backend ตรวจสิทธิ์ซ้ำเสมอ |
| Error | แสดง `err.message` จาก `ApiError` · 401 = token หมดอายุ (client จัดการให้), 409 = จองซ้อน/ข้อมูลซ้ำ |
| ทุกหน้า | มีสถานะ loading / empty / error ด้วย component ใน `ui.jsx` |

## เพิ่มหน้าใหม่

1. สร้าง component ใน `src/pages/...` ดึงข้อมูลด้วย `useApi(() => api('/path'), [deps])`
2. เพิ่ม `<Route>` ใน `src/App.jsx` ห่อด้วย `RequireRole` ถ้าต้อง login
3. เพิ่มลิงก์ใน `STUDENT_LINKS` หรือ `STAFF_LINKS` ใน `Layout.jsx`

รายการ endpoint ทั้งหมดอยู่ใน `backend/API.md` หรือ Swagger ที่ `http://localhost:8000/api/v1/docs`
