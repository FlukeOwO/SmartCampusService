# Smart Campus Service Platform

ระบบจองห้อง จองอุปกรณ์ และแจ้งปัญหา/ส่งคำร้อง สำหรับมหาวิทยาลัย
Backend เป็น FastAPI + PostgreSQL ที่ deploy บน Google Cloud Run ได้ และรันบนเครื่องตัวเองได้ด้วย Docker

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://www.postgresql.org)

## สารบัญ

- [ทำอะไรได้บ้าง](#ทำอะไรได้บ้าง)
- [เริ่มใช้งานบนเครื่องตัวเอง](#เริ่มใช้งานบนเครื่องตัวเอง)
- [บัญชีทดลอง](#บัญชีทดลอง)
- [คำสั่งที่ใช้บ่อย](#คำสั่งที่ใช้บ่อย)
- [โครงสร้างโปรเจกต์](#โครงสร้างโปรเจกต์)
- [สถาปัตยกรรม](#สถาปัตยกรรม)
- [Deploy ขึ้น cloud](#deploy-ขึ้น-cloud)
- [แก้ปัญหาเบื้องต้น](#แก้ปัญหาเบื้องต้น)
- [เอกสารอื่น](#เอกสารอื่น)

## ทำอะไรได้บ้าง

| ฟีเจอร์ | รายละเอียด |
|---|---|
| **Authentication** | สมัคร, login, refresh token ด้วย JWT และแบ่งสิทธิ์เป็น `student`, `staff`, `admin` |
| **จองห้อง/อุปกรณ์** | ส่งคำขอจอง รอ staff อนุมัติ และกันจองซ้อนเวลา (ตอบ `409`) |
| **คำร้อง/แจ้งปัญหา** | แนบไฟล์ได้ มอบหมายงาน เปลี่ยนสถานะ และให้คะแนนหลังเสร็จ |
| **ห้องและอุปกรณ์** | staff เพิ่ม แก้ ลบ ข้อมูลห้องและอุปกรณ์ |
| **การแจ้งเตือน** | แจ้งผู้ใช้ในระบบเมื่อสถานะคำร้องหรือการจองเปลี่ยน |
| **ไฟล์แนบ** | เก็บในโฟลเดอร์บนเครื่อง (dev) หรือ Cloud Storage แบบ private (cloud) |

## เริ่มใช้งานบนเครื่องตัวเอง

ใช้เวลาประมาณ 10 นาที ต้องมี [Docker Desktop](https://www.docker.com/products/docker-desktop/) และ Git

**1. ดึงโค้ดและสร้างไฟล์ `.env`**

```bash
git clone https://github.com/FlukeOwO/SmartCampusService.git
cd SmartCampusService
cp .env.example .env
```

ค่าใน `.env.example` ใช้รันบนเครื่องได้เลย ก่อนขึ้น cloud ให้สร้าง `SECRET_KEY` ใหม่ด้วย
`python -c "import secrets; print(secrets.token_urlsafe(48))"`

**2. เปิดระบบ สร้างตาราง และใส่ข้อมูลตัวอย่าง**

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec -e SEED_DEMO_DATA=true backend python seed.py
```

**3. เปิดใช้งาน**

| บริการ | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/api/v1/docs |
| PostgreSQL | `localhost:5432` |

**4. ลองเรียก API**

```bash
curl http://localhost:8000/healthz

curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "student1@smartcampus.dev", "password": "student12345"}'
```

ผลลัพธ์มี `access_token` ให้ใส่ใน header `Authorization: Bearer your_access_token_here`
ทุก endpoint (ยกเว้น register, login, refresh และ health check) ต้องแนบ token

ถ้าไม่มี `make` บน Windows ใช้คำสั่ง `docker compose` ตามด้านบนได้เลย

## บัญชีทดลอง

`seed.py` สร้างบัญชีเหล่านี้เมื่อตั้ง `SEED_DEMO_DATA=true` ใช้บนเครื่อง dev เท่านั้น
รหัสผ่านเป็นที่รู้กันทั่วไป **ห้ามใช้บน prod**

| Role | Email | Password |
|---|---|---|
| staff | staff@smartcampus.dev | staff12345 |
| student | student1@smartcampus.dev | student12345 |
| student | student2@smartcampus.dev | student12345 |

บัญชี admin สร้างจาก `SEED_ADMIN_EMAIL` และ `SEED_ADMIN_PASSWORD` (อย่างน้อย 12 ตัวอักษร)

## คำสั่งที่ใช้บ่อย

รันที่โฟลเดอร์หลักของโปรเจกต์

| ต้องการ | คำสั่ง |
|---|---|
| เปิด / ปิดระบบ | `docker compose up -d` / `docker compose down` |
| ดู log ของ backend | `docker compose logs -f backend` |
| ล้างข้อมูลทั้งหมด (รวม database) | `docker compose down -v` |
| เข้า shell ของ backend | `docker compose exec backend bash` |
| รัน test | `make test` |
| ตรวจโค้ด (lint) | `make lint` |

`make test` สร้างและใช้ database แยกชื่อ `campus_test` ให้เอง จึงไม่กระทบข้อมูลที่ใช้พัฒนา

**Migration (แก้โครงสร้าง database)**

```bash
# สร้างไฟล์ migration หลังแก้ model
docker compose exec backend alembic revision --autogenerate -m "describe_your_change_here"

docker compose exec backend alembic upgrade head     # ใช้ migration ล่าสุด
docker compose exec backend alembic downgrade -1     # ย้อน 1 ขั้น
```

**รัน backend โดยไม่ใช้ Docker** (ต้องมี PostgreSQL 15 และ Python 3.11 ขึ้นไป)

```bash
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

## โครงสร้างโปรเจกต์

```
SmartCampusService/
├── backend/
│   ├── app/
│   │   ├── core/          # config, database, security, logging
│   │   ├── common/        # exceptions, constants, storage
│   │   ├── models/        # ตารางใน PostgreSQL (SQLAlchemy)
│   │   ├── schemas/       # รูปแบบ request/response (Pydantic)
│   │   └── modules/       # Router -> Service แยกตามโดเมน
│   │       ├── auth/
│   │       ├── requests/
│   │       ├── bookings/
│   │       ├── inventory/
│   │       └── notifications/
│   ├── alembic/           # migration
│   ├── tests/             # pytest (ต้องใช้ PostgreSQL)
│   └── Dockerfile         # target: development, production
├── frontend/              # React + Vite
├── infra/gcp/setup.sh     # ตั้งค่า GCP ครั้งแรก
├── .github/workflows/     # backend-ci.yml, backend-cd.yml
├── docker-compose.yml     # สภาพแวดล้อมสำหรับพัฒนา
└── .env.example           # ตัวอย่างค่า environment
```

## สถาปัตยกรรม

```
React  ->  FastAPI (Cloud Run)  ->  PostgreSQL (Cloud SQL)
                  |
                  +-->  Cloud Storage (ไฟล์แนบ)
```

Backend เป็นแอปเดียวที่แบ่งเป็น 5 โมดูลตามโดเมน ทุกโมดูลทำงานเป็นชั้น Router -> Service -> Model:

- **Router** รับ HTTP และตรวจ JWT กับ role
- **Service** ถือกฎธุรกิจ ตรวจเจ้าของข้อมูล และคุม transaction
- **Model** แมปตารางใน PostgreSQL

การกันจองซ้อนทำ 2 ชั้น ชั้นแรกล็อกแถวห้องหรืออุปกรณ์ด้วย `SELECT ... FOR UPDATE` แล้วตรวจเวลาทับกัน
ชั้นที่สองคือ exclusion constraint ใน PostgreSQL ที่ปฏิเสธช่วงเวลาซ้อนกัน แม้โค้ดจะพลาด

| Tech | เวอร์ชัน |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Frontend | React 19, Vite |
| Database | PostgreSQL 15 |
| Cloud | Cloud Run, Cloud SQL, Cloud Storage, Secret Manager, GitHub Actions |

## Deploy ขึ้น cloud

GitHub Actions deploy ให้อัตโนมัติเมื่อ push เข้า `dev` (ไปยัง dev) หรือ `main` (ไปยัง prod)
แต่ workflow จะ**ข้ามขั้น deploy** จนกว่าจะตั้ง repository variable `DEPLOY_ENABLED=true`
จึงพัฒนาและ merge PR บน local ได้ก่อนโดยไม่ต้องมี GCP

ขั้นตอนตั้งค่า GCP ครั้งแรก ตัวแปรของ GitHub และวิธี rollback อยู่ใน [DEPLOYMENT.md](DEPLOYMENT.md)

## แก้ปัญหาเบื้องต้น

**Backend ไม่ขึ้น**

```bash
docker compose logs backend
docker compose ps
```

ข้อผิดพลาดที่พบบ่อยคือ `SECRET_KEY` ใน `.env` สั้นกว่า 32 ตัวอักษร หรือไม่มีไฟล์ `.env`

**เชื่อมต่อ database ไม่ได้**

```bash
docker compose ps db
docker compose logs db
docker compose exec backend alembic current
```

ถ้า `alembic current` ว่าง แปลว่ายังไม่ได้รัน `alembic upgrade head`

**ตารางหรือข้อมูลเพี้ยนหลังแก้ migration** ล้างแล้วเริ่มใหม่ด้วย `docker compose down -v`
(ข้อมูลใน database หายทั้งหมด)

**`pip install` ขึ้น `UnicodeDecodeError`** ไฟล์ `requirements.txt` ต้องเป็น UTF-8
บน Windows PowerShell การใช้ `>` เขียนไฟล์จะได้ UTF-16 ให้ใช้ text editor บันทึกเป็น UTF-8 แทน

## เอกสารอื่น

- [API reference](backend/API.md) รายการ endpoint สิทธิ์ และรูปแบบ error
- [Deployment guide](DEPLOYMENT.md) ตั้งค่าและ deploy บน Google Cloud
