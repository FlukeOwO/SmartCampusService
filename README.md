# Smart Campus Service Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com)

ระบบ Smart Campus Service Platform แบบ Cloud-Ready สำหรับจัดการการจองห้องและอุปกรณ์ พร้อมระบบแจ้งปัญหาและคำร้อง

## 🌟 Features

- ✅ **Authentication & RBAC** - JWT-based authentication with role-based access control
- ✅ **Room Booking** - จองห้องเรียน/ประชุม พร้อมป้องกัน double booking
- ✅ **Equipment Booking** - จองอุปกรณ์ต่างๆ (Projector, Camera, Laptop)
- ✅ **Request Management** - แจ้งปัญหา/ส่งคำร้อง พร้อมแนบไฟล์
- ✅ **Transaction Locking** - Pessimistic locking เพื่อป้องกัน race condition
- ✅ **Cloud-Ready** - พร้อม deploy บน Google Cloud Run
- ✅ **Storage Abstraction** - รองรับทั้ง Local และ Google Cloud Storage

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   React     │─────▶│   FastAPI    │─────▶│ PostgreSQL  │
│  Frontend   │      │   Backend    │      │  Database   │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ Cloud Storage│
                     │  (Local/GCS) │
                     └──────────────┘
```

**Tech Stack:**
- **Backend**: FastAPI, SQLAlchemy 2.0 (Async), Alembic, Pydantic V2
- **Frontend**: React 18, Vite, TailwindCSS, React Query
- **Database**: PostgreSQL 15
- **Infrastructure**: Docker, Docker Compose, Google Cloud Platform

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (recommended) หรือ Docker Engine + Docker Compose
- Git
- (Optional) Python 3.11+ และ Node.js 18+ สำหรับ local development

### 1. Clone Repository

```bash
git clone <repository-url>
cd SmartCampusService
```

### 2. Setup Environment Variables

```bash
# สร้างไฟล์ .env จาก template
cp .env.example .env

# สร้าง SECRET_KEY สำหรับ JWT
python -c "import secrets; print(secrets.token_urlsafe(32))"

# แก้ไข .env และใส่ SECRET_KEY ที่สร้างได้
# vim .env  (หรือใช้ text editor อื่น)
```

**⚠️ สำคัญ**: ต้องแก้ไข `SECRET_KEY` ในไฟล์ `.env` ก่อนรัน!

### 3. Start Services

```bash
# Start all services (backend, frontend, database)
docker-compose up -d

# ดู logs
docker-compose logs -f backend

# ตรวจสอบสถานะ
docker-compose ps
```

### 4. Initialize Database

```bash
# Run database migrations
docker-compose exec backend alembic upgrade head

# Seed ข้อมูลตัวอย่าง (บัญชี demo, ห้อง, อุปกรณ์)
docker-compose exec -e SEED_DEMO_DATA=true backend python seed.py
```

### 5. Access Services

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/v1/docs
- **Alternative Docs**: http://localhost:8000/api/v1/redoc
- **Database**: localhost:5432

### 6. Test API

```bash
# Health check
curl http://localhost:8000/healthz

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student1@smartcampus.dev",
    "password": "student12345"
  }'

# List rooms (ต้องแนบ access_token)
curl http://localhost:8000/api/v1/inventory/rooms -H "Authorization: Bearer <access_token>"
```

## 🔑 Default Credentials

จาก `seed.py` เมื่อ `SEED_DEMO_DATA=true` (ใช้บนเครื่อง dev เท่านั้น):

| Role | Email | Password |
|------|-------|----------|
| Staff | staff@smartcampus.dev | staff12345 |
| Student | student1@smartcampus.dev | student12345 |
| Student | student2@smartcampus.dev | student12345 |

บัญชี admin สร้างด้วย `SEED_ADMIN_EMAIL` + `SEED_ADMIN_PASSWORD` (≥ 12 ตัวอักษร)

## 📁 Project Structure

```
SmartCampusService/
├── backend/                  # FastAPI Backend
│   ├── app/
│   │   ├── core/            # Config, Security, Database
│   │   ├── common/          # Storage, Exceptions, Constants
│   │   ├── models/          # SQLAlchemy Models
│   │   ├── schemas/         # Pydantic Schemas
│   │   └── modules/         # Router -> Service ต่อโดเมน
│   │       ├── auth/        # Register, login, refresh, RBAC
│   │       ├── requests/    # คำร้อง + ไฟล์แนบ + มอบหมายงาน
│   │       ├── bookings/    # จองห้อง/อุปกรณ์ + กันจองซ้อน
│   │       ├── inventory/   # Rooms & Equipment
│   │       └── notifications/
│   ├── alembic/            # Database Migrations
│   ├── tests/              # pytest (ต้องมี PostgreSQL)
│   ├── Dockerfile          # development / production targets
│   └── requirements.txt    # Python dependencies
├── infra/gcp/setup.sh      # ตั้งค่า GCP ครั้งแรก (VPC, Cloud SQL, WIF, Cloud Run)
├── .github/workflows/      # backend-ci.yml, backend-cd.yml
├── frontend/               # React Frontend
│   ├── src/
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml      # Development environment
├── .env.example           # Environment template
└── DEPLOYMENT.md          # Cloud Run + Cloud SQL deployment guide
```

## 🔧 Development Commands

### Docker Compose

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild images
docker-compose build --no-cache

# View logs
docker-compose logs -f [service_name]

# Execute command in container
docker-compose exec backend bash
docker-compose exec backend python seed.py

# Remove all (including volumes)
docker-compose down -v
```

### Database Migrations

```bash
# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback one migration
docker-compose exec backend alembic downgrade -1

# View migration history
docker-compose exec backend alembic history
```

### Backend Development

```bash
# Install dependencies locally
cd backend
pip install -r requirements.txt

# Run without Docker (ต้องมี PostgreSQL รันอยู่)
uvicorn app.main:app --reload
```

## 🧪 Testing

```bash
# Run tests (when implemented)
docker-compose exec backend pytest

# With coverage
docker-compose exec backend pytest --cov=app
```

## 📚 Documentation

- **[API Documentation](backend/API.md)** - Complete API reference
- **[Deployment Guide](DEPLOYMENT.md)** - Deploy to GCP Cloud Run
- **[Booking Service](backend/app/modules/bookings/README.md)** - Transaction locking details

## 🚢 Production Deployment

### Build Production Images

```bash
# Backend
cd backend
docker build --target production -t campus-backend:prod .

# Frontend
cd frontend
docker build --target production -t campus-frontend:prod .
```

### Deploy to Google Cloud Run

ดูรายละเอียดครบใน **[DEPLOYMENT.md](DEPLOYMENT.md)**

```bash
# Build and push
docker build --target production -t gcr.io/PROJECT_ID/campus-backend .
docker push gcr.io/PROJECT_ID/campus-backend

# Deploy
gcloud run deploy campus-backend \
  --image gcr.io/PROJECT_ID/campus-backend \
  --platform managed \
  --region asia-southeast1
```

## 🛠️ Troubleshooting

### Git Repository Cleanup (First Time Setup)

ถ้าโคลนมาแล้วเจอ `venv/`, `node_modules/`, หรือ `*.db` ถูก track:

```bash
# บน Windows (PowerShell)
.\git-cleanup.ps1

# บน Linux/Mac
chmod +x .git-cleanup.sh
./.git-cleanup.sh

# จากนั้น commit การเปลี่ยนแปลง
git commit -m "chore: remove tracked files that should be ignored"
```

### Backend ไม่ขึ้น

```bash
# ดู logs
docker-compose logs backend

# ตรวจสอบ .env
cat .env | grep SECRET_KEY

# ตรวจสอบ database connection
docker-compose exec backend python -c "from app.core.database import check_db_connection; import asyncio; print(asyncio.run(check_db_connection()))"
```

### Database connection failed

```bash
# ตรวจสอบ PostgreSQL
docker-compose ps db
docker-compose logs db

# ตรวจสอบว่า migrations รันแล้ว
docker-compose exec backend alembic current
```

### Requirements.txt encoding issue

ถ้าเจอ error "UnicodeDecodeError" เวลา `pip install`:

```bash
# Re-save as UTF-8
# ไฟล์ requirements.txt ต้องเป็น UTF-8 เท่านั้น
# บน Windows ถ้าใช้ PowerShell redirect (>) จะได้ UTF-16
# ให้ใช้ text editor save เป็น UTF-8 แทน
```

## 🔐 Security Notes

- ✅ เปลี่ยน `SECRET_KEY` ใน production
- ✅ ใช้ HTTPS ใน production
- ✅ อย่า commit `.env` file
- ✅ ใช้ Secret Manager สำหรับ sensitive data
- ✅ Enable rate limiting
- ✅ Regular security updates

## 📝 License

MIT License

## 👥 Contributors

- Your Team

## 📞 Support

- Issues: GitHub Issues
- Docs: `/api/v1/docs`
- Email: support@smartcampus.dev

---

**Built with ❤️ using FastAPI, React, and PostgreSQL**
#   S m a r t C a m p u s S e r v i c e 
 
 #   S m a r t C a m p u s S e r v i c e 
 
 