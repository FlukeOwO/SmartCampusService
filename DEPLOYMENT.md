# Deployment — Backend บน Google Cloud (Cloud Run + Cloud SQL)

อ้างอิงเอกสารออกแบบ *Smart Campus — Backend & Cloud Design (GCP)* และ [docs/CLOUD_DESIGN.md](docs/CLOUD_DESIGN.md)
(เหตุผลการเลือกบริการ แผนภาพ และสคริปต์สาธิต)

```
GitHub Actions ──(WIF, ไม่มี JSON key)──► Artifact Registry  campus/api:<git-sha>
      │                                          │
      ├─► Cloud Run Job  campus-migrate  (alembic upgrade head)
      └─► Cloud Run      campus-api  ──Direct VPC Egress──► Cloud SQL PostgreSQL 15 (private IP, SSL)
                              │                               campus-vpc / campus-run-subnet 10.10.0.0/24
                              ├─► Secret Manager  db-password, jwt-secret-key
                              └─► GCS  <project>-campus-uploads (private, Signed URL 15 นาที)
```

| ส่วน | Resource (prod) | dev |
|---|---|---|
| API | Cloud Run `campus-api` (1 vCPU / 512 MiB, min 0 / max 3, concurrency 80) | `campus-api-dev` (max 1) |
| Migration | Cloud Run Job `campus-migrate` | `campus-migrate-dev` |
| Seed | Cloud Run Job `campus-seed` (รันมือครั้งเดียว) | `campus-seed-dev` |
| Database | Cloud SQL `campus-db` → DB `smart_campus`, user `campus_app` | DB `smart_campus_dev`, user `campus_app_dev` |
| ไฟล์แนบ | `gs://<project>-campus-uploads` (private, lifecycle Nearline 30 วัน / Coldline 180 วัน) | `...-campus-uploads-dev` |
| Frontend | `gs://<project>-campus-web` (public) | `...-campus-web-dev` |
| Secrets | `db-password`, `jwt-secret-key` | `...-dev` |
| Runtime SA | `campus-api-sa` | `campus-api-dev-sa` |
| Image | `asia-southeast1-docker.pkg.dev/<project>/campus/api:<git-sha>` | เหมือนกัน |

## 1. ตั้งค่าครั้งแรก (Owner ของ project, ใน Cloud Shell)

```bash
git clone https://github.com/FlukeOwO/SmartCampusService && cd SmartCampusService/infra/gcp
export PROJECT_ID=smart-campus-prod          # REGION ค่าเริ่มต้น asia-southeast1

./setup.sh shared                             # API, VPC, PSA, Cloud SQL, Artifact Registry, WIF, github-deployer
./setup.sh env dev                            # API, DB, secrets, buckets, jobs ของ dev
./setup.sh env prod
./setup.sh seed prod admin@<university-domain>   # สร้าง admin คนแรก (ถามรหัสผ่าน, เก็บใน Secret Manager)
./setup.sh dashboard prod                     # Cloud Monitoring dashboard (และ dev)
./setup.sh budget <BILLING_ACCOUNT_ID>        # budget $300 (50/75/90% + forecast 100%) + $20/เดือน
```

`env` ตั้ง `CORS_ORIGINS=https://storage.googleapis.com` ให้ตรงกับเว็บที่โฮสต์บน bucket
ถ้า frontend ใช้โดเมนอื่น ส่งเป็นอาร์กิวเมนต์ที่ 3 เช่น `./setup.sh env prod https://campus.example.com`

สคริปต์รันซ้ำได้ (resource ที่มีแล้วจะข้าม) จากนั้นตั้ง **startup probe** `HTTP GET /healthz`
ที่ Console › Cloud Run › service › Edit › Health checks ทั้ง dev และ prod

> dev ใส่ข้อมูลตัวอย่างได้ด้วย `SEED_DEMO_DATA=true ./setup.sh seed dev <email>` — **ห้ามใช้กับ prod**
> เพราะบัญชี demo ใช้รหัสผ่านที่รู้กันทั่วไป

## 2. ตั้งค่า GitHub

**Settings › Environments** สร้าง `dev` และ `prod` (prod ใส่ *Required reviewers*) แล้วใส่ **Variables**
(ไม่มี secret ของ GCP ใน GitHub เลย):

| Variable | dev | prod |
|---|---|---|
| `GCP_PROJECT_ID` | `smart-campus-prod` | `smart-campus-prod` |
| `GCP_REGION` | `asia-southeast1` | `asia-southeast1` |
| `WIF_PROVIDER` | `projects/<number>/locations/global/workloadIdentityPools/github/providers/smart-campus` | เหมือนกัน |
| `DEPLOYER_SA` | `github-deployer@<project>.iam.gserviceaccount.com` | เหมือนกัน |
| `SERVICE_NAME` | `campus-api-dev` | `campus-api` |
| `MIGRATE_JOB` | `campus-migrate-dev` | `campus-migrate` |
| `WEB_BUCKET` | `<project>-campus-web-dev` | `<project>-campus-web` |
| `API_BASE_URL` | `https://campus-api-dev-....run.app/api/v1` | `https://campus-api-....run.app/api/v1` |

ค่าเหล่านี้ `setup.sh` พิมพ์ออกมาให้ตอนจบแต่ละขั้น

สุดท้ายเปิดการ deploy: **Settings › Secrets and variables › Actions › Variables** (ระดับ repository)
เพิ่ม `DEPLOY_ENABLED` = `true` — ถ้ายังไม่ตั้ง ขั้น deploy ของ `backend-cd` และ `frontend-cd` จะถูกข้าม (skipped) ทุกครั้ง
ทำให้ทำงานบน local และ merge PR ได้ก่อนที่ cloud จะพร้อม

**Branch protection**: `main` ห้าม push ตรง, merge ผ่าน PR จาก `dev`, ต้องผ่าน `backend-ci` + review 1 คน;
`dev` merge ผ่าน PR และต้องผ่าน `backend-ci`

## 3. Pipeline

| Workflow | Trigger | ขั้นตอน |
|---|---|---|
| `.github/workflows/backend-ci.yml` | PR เข้า `dev`/`main`, push ที่แก้ `backend/**` | `ruff check` + `ruff format --check` → `alembic upgrade/downgrade/upgrade` → `pytest` (PostgreSQL 15) → `docker build --target production` |
| `.github/workflows/backend-cd.yml` | push `dev` → env `dev`, push `main` → env `prod` | WIF auth → build + push `:<git-sha>` → migration job → deploy revision แบบ `--no-traffic` → smoke test `/healthz` บน tag URL → ย้าย traffic 100% (รันด้วยมือใส่ `traffic_percent` เพื่อทำ canary ได้) |
| `.github/workflows/frontend-cd.yml` | PR/push ที่แก้ `frontend/**` | lint + build ทุกครั้ง · push `dev`/`main` → `vite build --base=/<bucket>/` → `gcloud storage rsync` ไป `WEB_BUCKET` → smoke test |

จุดที่ pipeline หยุดได้ 3 จุด: **CI ไม่ผ่าน**, **migration ล้ม**, **smoke test ล้ม** —
ทั้งสามกรณี revision เดิมยังรับ traffic อยู่ (deploy แบบ no-traffic จึงไม่ต้อง rollback อัตโนมัติ)

### Rollback, canary และงานดูแลระบบ (`infra/gcp/ops.sh`)

```bash
./ops.sh status   prod            # revision ที่รับ traffic + สถานะ DB
./ops.sh rollback prod            # กลับ revision ก่อนหน้า 100% (หรือระบุชื่อ revision)
./ops.sh canary   prod 10         # ส่ง 10% ไป revision ล่าสุด
./ops.sh promote  prod            # revision ล่าสุด 100%
./ops.sh db-ha    on|off          # Cloud SQL High Availability 2 zone (เปิดช่วงสาธิต)
./ops.sh db-stop | db-start       # หยุด/เปิด DB ช่วงไม่ใช้งาน
./ops.sh teardown                 # ลบ project หลังจบรายวิชา
```

Migration ต้องเข้ากันได้กับโค้ดเวอร์ชันก่อน (expand → contract): เพิ่มคอลัมน์ใหม่แบบ nullable ก่อน
แล้วค่อยลบคอลัมน์เก่าใน release ถัดไป จึง rollback โค้ดได้โดยไม่ต้อง downgrade DB

## 4. Environment variables ใน container

| Env | ที่มา | prod |
|---|---|---|
| `ENVIRONMENT`, `DEBUG` | env | `production`, `false` (dev ใช้ `staging` → เปิด Swagger) |
| `POSTGRES_SERVER`, `POSTGRES_PORT` | env | private IP ของ `campus-db`, `5432` |
| `POSTGRES_USER`, `POSTGRES_DB` | env | `campus_app`, `smart_campus` |
| `POSTGRES_PASSWORD` | Secret Manager | `db-password:latest` |
| `SECRET_KEY` | Secret Manager | `jwt-secret-key:latest` |
| `DB_SSL` | env | `require` (Cloud SQL `ENCRYPTED_ONLY`) |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | env | `3`, `2` |
| `STORAGE_PROVIDER`, `GCS_BUCKET_NAME`, `GCS_PROJECT_ID` | env | `gcs`, `<project>-campus-uploads`, `<project>` |
| `CORS_ORIGINS` | env | URL ของ Frontend เท่านั้น |
| `ALLOWED_HOSTS` | env | `*.run.app` (+ custom domain ถ้ามี) |
| `LOG_LEVEL`, `LOG_FORMAT` | env | `INFO`, `json` |
| `GCP_PROJECT_ID` | env | `<project>` (ผูก log กับ trace ของ request) |
| `PORT` | Cloud Run | ห้ามตั้งทับ |

เปลี่ยนค่า secret (rotate) แล้วต้อง deploy revision ใหม่ เพราะค่าจาก Secret Manager อ่านตอน instance เริ่ม:
```bash
openssl rand -base64 48 | tr -d '\n' | gcloud secrets versions add jwt-secret-key --data-file=-
gcloud run services update campus-api --region asia-southeast1 --update-labels=rotated=$(date +%s)
```

## 5. Connection budget

แต่ละ instance เปิด connection ได้สูงสุด `DB_POOL_SIZE + DB_MAX_OVERFLOW` = 5 →
prod 3×5 + dev 1×5 + migration job ≈ 21 connection ขณะที่ `db-f1-micro` รับได้น้อย
ตรวจค่าจริงด้วย `SHOW max_connections;` ก่อนเพิ่ม `max-instances`

## 6. ประหยัดค่าใช้จ่าย

- Cloud Run `min-instances=0` (scale-to-zero), request-based billing
- ช่วงไม่ใช้ระบบนาน ๆ: `./ops.sh db-stop` (เปิดคืน `./ops.sh db-start`)
- Artifact Registry เก็บแค่ 10 image ล่าสุด, ไฟล์แนบเก่าย้ายไป storage class ที่ถูกกว่าอัตโนมัติ
- Cloud SQL HA เปิดเฉพาะช่วงสาธิต (`./ops.sh db-ha on`, จบแล้ว `off`)
- จบรายวิชา: `./ops.sh teardown`

## 7. Local development

```bash
cp .env.example .env
make start && make migrate && make seed     # http://localhost:8000/api/v1/docs
make test                                   # pytest กับ DB แยก campus_test
```
