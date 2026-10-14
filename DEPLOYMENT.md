# Deployment — Backend บน Google Cloud (Cloud Run + Cloud SQL)

อ้างอิงเอกสารออกแบบ *Smart Campus — Backend & Cloud Design (GCP)*

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
| ไฟล์แนบ | `gs://<project>-campus-uploads` | `...-campus-uploads-dev` |
| Secrets | `db-password`, `jwt-secret-key` | `...-dev` |
| Runtime SA | `campus-api-sa` | `campus-api-dev-sa` |
| Image | `asia-southeast1-docker.pkg.dev/<project>/campus/api:<git-sha>` | เหมือนกัน |

## 1. ตั้งค่าครั้งแรก (Owner ของ project, ใน Cloud Shell)

```bash
git clone https://github.com/FlukeOwO/SmartCampusService && cd SmartCampusService/infra/gcp
export PROJECT_ID=smart-campus-prod          # REGION ค่าเริ่มต้น asia-southeast1

./setup.sh shared                             # API, VPC, PSA, Cloud SQL, Artifact Registry, WIF, github-deployer
./setup.sh env dev  https://<frontend-dev-domain>
./setup.sh env prod https://<frontend-domain>
./setup.sh seed prod admin@<university-domain>   # สร้าง admin คนแรก (ถามรหัสผ่าน, เก็บใน Secret Manager)
./setup.sh budget <BILLING_ACCOUNT_ID>        # budget $300 (50/75/90%) + $20/เดือน
```

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

ค่าเหล่านี้ `setup.sh` พิมพ์ออกมาให้ตอนจบแต่ละขั้น

**Branch protection**: `main` ห้าม push ตรง, merge ผ่าน PR จาก `dev`, ต้องผ่าน `backend-ci` + review 1 คน;
`dev` merge ผ่าน PR และต้องผ่าน `backend-ci`

## 3. Pipeline

| Workflow | Trigger | ขั้นตอน |
|---|---|---|
| `.github/workflows/backend-ci.yml` | PR เข้า `dev`/`main`, push ที่แก้ `backend/**` | `ruff check` + `ruff format --check` → `alembic upgrade/downgrade/upgrade` → `pytest` (PostgreSQL 15) → `docker build --target production` |
| `.github/workflows/backend-cd.yml` | push `dev` → env `dev`, push `main` → env `prod` | WIF auth → build + push `:<git-sha>` → migration job → deploy revision แบบ `--no-traffic` → smoke test `/healthz` บน tag URL → ย้าย traffic 100% |

จุดที่ pipeline หยุดได้ 3 จุด: **CI ไม่ผ่าน**, **migration ล้ม**, **smoke test ล้ม** —
ทั้งสามกรณี revision เดิมยังรับ traffic อยู่ (deploy แบบ no-traffic จึงไม่ต้อง rollback อัตโนมัติ)

### Rollback

```bash
gcloud run revisions list --service campus-api --region asia-southeast1
gcloud run services update-traffic campus-api --region asia-southeast1 --to-revisions=<revision-เดิม>=100
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
- ช่วงไม่ใช้ระบบนาน ๆ: `gcloud sql instances patch campus-db --activation-policy=NEVER` (เปิดคืน `ALWAYS`)
- Artifact Registry เก็บแค่ 10 image ล่าสุด
- จบรายวิชา: `gcloud projects delete <project>`

## 7. Local development

```bash
cp .env.example .env
make start && make migrate && make seed     # http://localhost:8000/api/v1/docs
make test                                   # pytest กับ DB แยก campus_test
```
