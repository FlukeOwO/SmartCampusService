#!/usr/bin/env bash
# =============================================================================
# Smart Campus - one-time GCP setup (Cloud Run + Cloud SQL private IP + GCS)
#
# รันใน Cloud Shell โดยคนที่เป็น Owner ของ project:
#   export PROJECT_ID=smart-campus-prod
#   ./setup.sh shared                 # VPC, PSA, Cloud SQL, Artifact Registry, WIF, deployer SA
#   ./setup.sh env dev                # API + DB + buckets ของ dev
#   ./setup.sh env prod
#   ./setup.sh seed prod admin@your-university.ac.th   # สร้างบัญชี admin คนแรก (ครั้งเดียว)
#   ./setup.sh dashboard prod         # Cloud Monitoring dashboard (Observability)
#   ./setup.sh budget <BILLING_ACCOUNT_ID>
#
# Frontend โฮสต์บน bucket สาธารณะ คนละ origin ต่อ bucket:
#   https://<project>-campus-web.storage.googleapis.com/index.html
# ห้ามใช้ https://storage.googleapis.com เพราะเป็น origin ร่วมของทุก bucket (localStorage ของ token รั่วได้)
# ถ้าใช้โดเมนอื่น ส่งเป็นอาร์กิวเมนต์ที่ 3: ./setup.sh env prod https://campus.example.com
# งานหลังติดตั้ง (เปิด HA, หยุด DB, canary, rollback, ลบ project) อยู่ใน ./ops.sh
#
# รันซ้ำได้: resource ที่มีอยู่แล้วจะถูกข้าม
# =============================================================================
set -euo pipefail

: "${PROJECT_ID:?export PROJECT_ID first}"
REGION="${REGION:-asia-southeast1}"
REPO="${REPO:-Nolimx/SmartCampusService}"

VPC=campus-vpc
SUBNET=campus-run-subnet
SUBNET_RANGE=10.10.0.0/24
PSA_RANGE_NAME=campus-psa-range
PSA_RANGE_START=10.20.0.0
SQL_INSTANCE=campus-db
AR_REPO=campus
# prod ใช้ github-deployer (ชื่อเดิม) , dev ใช้คนละ service account
PROD_DEPLOYER_SA="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
DEV_DEPLOYER_SA="github-deployer-dev@${PROJECT_ID}.iam.gserviceaccount.com"

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
exists() { "$@" >/dev/null 2>&1; }

STARTUP_PROBE="httpGet.path=/healthz,initialDelaySeconds=0,timeoutSeconds=4,periodSeconds=5,failureThreshold=12"

ensure_deployer() {
  local sa_email=$1
  local sa_id=${sa_email%%@*}
  exists gcloud iam service-accounts describe "$sa_email" ||
    gcloud iam service-accounts create "$sa_id" --display-name="GitHub Actions deployer ($sa_id)"
  gcloud artifacts repositories add-iam-policy-binding "$AR_REPO" --location="$REGION" \
    --member="serviceAccount:$sa_email" --role=roles/artifactregistry.writer >/dev/null
}

bind_deployer_wif() {
  local sa_email=$1 subject=$2 project_number=$3
  gcloud iam service-accounts add-iam-policy-binding "$sa_email" \
    --role=roles/iam.workloadIdentityUser \
    --member="principal://iam.googleapis.com/projects/${project_number}/locations/global/workloadIdentityPools/github/subject/${subject}" \
    >/dev/null
}

gcloud config set project "$PROJECT_ID" >/dev/null

# -----------------------------------------------------------------------------
shared() {
  log "1) Enable APIs"
  gcloud services enable run.googleapis.com sqladmin.googleapis.com compute.googleapis.com \
    servicenetworking.googleapis.com artifactregistry.googleapis.com \
    secretmanager.googleapis.com iam.googleapis.com iamcredentials.googleapis.com \
    sts.googleapis.com storage.googleapis.com monitoring.googleapis.com \
    logging.googleapis.com cloudtrace.googleapis.com billingbudgets.googleapis.com

  log "2) VPC + subnet for Direct VPC Egress"
  exists gcloud compute networks describe "$VPC" ||
    gcloud compute networks create "$VPC" --subnet-mode=custom
  exists gcloud compute networks subnets describe "$SUBNET" --region="$REGION" ||
    gcloud compute networks subnets create "$SUBNET" --network="$VPC" --region="$REGION" \
      --range="$SUBNET_RANGE" --enable-private-ip-google-access

  log "3) Private Services Access (Cloud SQL private IP)"
  exists gcloud compute addresses describe "$PSA_RANGE_NAME" --global ||
    gcloud compute addresses create "$PSA_RANGE_NAME" --global --purpose=VPC_PEERING \
      --addresses="$PSA_RANGE_START" --prefix-length=20 --network="$VPC"
  gcloud services vpc-peerings connect --service=servicenetworking.googleapis.com \
    --ranges="$PSA_RANGE_NAME" --network="$VPC" 2>/dev/null ||
    gcloud services vpc-peerings update --service=servicenetworking.googleapis.com \
      --ranges="$PSA_RANGE_NAME" --network="$VPC" --force

  log "4) Cloud SQL PostgreSQL 15 (private IP only, SSL required)"
  # backup 19:00 UTC = 02:00 เวลาไทย, maintenance เสาร์ 20:00 UTC = อาทิตย์ 03:00 เวลาไทย
  exists gcloud sql instances describe "$SQL_INSTANCE" ||
    gcloud sql instances create "$SQL_INSTANCE" --database-version=POSTGRES_15 \
      --edition=ENTERPRISE --tier=db-f1-micro --region="$REGION" \
      --network="projects/$PROJECT_ID/global/networks/$VPC" --no-assign-ip \
      --storage-type=SSD --storage-size=10 --storage-auto-increase \
      --backup-start-time=19:00 --retained-backups-count=7 \
      --enable-point-in-time-recovery \
      --maintenance-window-day=SAT --maintenance-window-hour=20 \
      --ssl-mode=ENCRYPTED_ONLY
  # instance ที่มีอยู่แล้ว (สร้างก่อนมี flag นี้) ต้อง patch แยก
  gcloud sql instances patch "$SQL_INSTANCE" --enable-point-in-time-recovery --quiet

  log "5) Artifact Registry (keep 10 newest images)"
  exists gcloud artifacts repositories describe "$AR_REPO" --location="$REGION" ||
    gcloud artifacts repositories create "$AR_REPO" --repository-format=docker \
      --location="$REGION"
  local policy
  policy=$(mktemp)
  cat >"$policy" <<'JSON'
[{"name":"keep-10","action":{"type":"Keep"},"mostRecentVersions":{"keepCount":10}},
 {"name":"delete-old","action":{"type":"Delete"},"condition":{"olderThan":"30d"}}]
JSON
  gcloud artifacts repositories set-cleanup-policies "$AR_REPO" --location="$REGION" \
    --policy="$policy" --no-dry-run
  rm -f "$policy"

  log "6) GitHub deployer service accounts (dev and prod are separate)"
  ensure_deployer "$PROD_DEPLOYER_SA"
  ensure_deployer "$DEV_DEPLOYER_SA"
  # run.developer แบบทั้ง project ถูกถอดตอน ./setup.sh env prod หลังผูกสิทธิ์ราย service แล้ว

  log "7) Workload Identity Federation (this repo, and only the dev/prod GitHub Environments)"
  local project_number
  project_number=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
  exists gcloud iam workload-identity-pools describe github --location=global ||
    gcloud iam workload-identity-pools create github --location=global --display-name="GitHub"
  if ! exists gcloud iam workload-identity-pools providers describe smart-campus \
    --location=global --workload-identity-pool=github; then
    gcloud iam workload-identity-pools providers create-oidc smart-campus --location=global \
      --workload-identity-pool=github --issuer-uri="https://token.actions.githubusercontent.com" \
      --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
      --attribute-condition="assertion.repository == '$REPO'"
  fi
  # รันซ้ำแล้วต้องอัปเดต condition ด้วย (create อย่างเดียวไม่แก้ของเดิม)
  gcloud iam workload-identity-pools providers update-oidc smart-campus --location=global \
    --workload-identity-pool=github \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository == '$REPO'"
  # subject เป็น environment เมื่อ job ตั้ง environment: (ไม่ใช่ ref)
  bind_deployer_wif "$PROD_DEPLOYER_SA" "repo:${REPO}:environment:prod" "$project_number"
  bind_deployer_wif "$DEV_DEPLOYER_SA" "repo:${REPO}:environment:dev" "$project_number"

  log "Done. GitHub Environment variables:"
  echo "  GCP_PROJECT_ID = $PROJECT_ID"
  echo "  GCP_REGION     = $REGION"
  echo "  WIF_PROVIDER   = projects/$project_number/locations/global/workloadIdentityPools/github/providers/smart-campus"
  echo "  DEPLOYER_SA (prod) = $PROD_DEPLOYER_SA"
  echo "  DEPLOYER_SA (dev)  = $DEV_DEPLOYER_SA"
  echo "Then run ./setup.sh env dev and ./setup.sh env prod before the next deploy."
}

# -----------------------------------------------------------------------------
# ชื่อ resource ต่อ environment: prod ไม่มี suffix, dev ต่อท้าย -dev
env_names() {
  local env=$1
  case "$env" in
    prod) SUFFIX=""; DB_NAME=smart_campus; DB_USER=campus_app; APP_ENV=production; MAX_INSTANCES=3 ;;
    dev) SUFFIX="-dev"; DB_NAME=smart_campus_dev; DB_USER=campus_app_dev; APP_ENV=staging; MAX_INSTANCES=1 ;;
    *) echo "env must be prod or dev" >&2; exit 1 ;;
  esac
  if [ "$env" = "prod" ]; then
    DEPLOYER_SA="$PROD_DEPLOYER_SA"
  else
    DEPLOYER_SA="$DEV_DEPLOYER_SA"
  fi
  SERVICE="campus-api${SUFFIX}"
  MIGRATE_JOB="campus-migrate${SUFFIX}"
  SEED_JOB="campus-seed${SUFFIX}"
  API_SA_NAME="campus-api${SUFFIX}-sa"
  API_SA="${API_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
  BUCKET="${PROJECT_ID}-campus-uploads${SUFFIX}"
  WEB_BUCKET="${PROJECT_ID}-campus-web${SUFFIX}"
  SECRET_DB="db-password${SUFFIX}"
  SECRET_JWT="jwt-secret-key${SUFFIX}"
}

env_setup() {
  local env=$1
  env_names "$env"
  local frontend_origin=${2:-}
  if [ -z "$frontend_origin" ]; then
    frontend_origin="https://${WEB_BUCKET}.storage.googleapis.com"
  fi
  if [ "$frontend_origin" = "https://storage.googleapis.com" ] || [ "$frontend_origin" = "https://storage.googleapis.com/" ]; then
    echo "Refusing CORS origin https://storage.googleapis.com (shared by every public GCS bucket)." >&2
    echo "Default is https://${WEB_BUCKET}.storage.googleapis.com — pass that, or your own exact origin." >&2
    exit 1
  fi
  local db_host
  db_host=$(gcloud sql instances describe "$SQL_INSTANCE" --format='value(ipAddresses[0].ipAddress)')

  log "[$env] Database + user"
  exists gcloud sql databases describe "$DB_NAME" --instance="$SQL_INSTANCE" ||
    gcloud sql databases create "$DB_NAME" --instance="$SQL_INSTANCE"
  if ! exists gcloud secrets describe "$SECRET_DB"; then
    local db_pass
    db_pass=$(openssl rand -base64 24 | tr -d '/+=')
    if gcloud sql users list --instance="$SQL_INSTANCE" --format='value(name)' | grep -qx "$DB_USER"; then
      gcloud sql users set-password "$DB_USER" --instance="$SQL_INSTANCE" --password="$db_pass"
    else
      gcloud sql users create "$DB_USER" --instance="$SQL_INSTANCE" --password="$db_pass"
    fi
    printf '%s' "$db_pass" | gcloud secrets create "$SECRET_DB" --data-file=- \
      --replication-policy=user-managed --locations="$REGION"
    unset db_pass
  fi

  log "[$env] JWT secret"
  exists gcloud secrets describe "$SECRET_JWT" ||
    openssl rand -base64 48 | tr -d '\n' | gcloud secrets create "$SECRET_JWT" --data-file=- \
      --replication-policy=user-managed --locations="$REGION"

  log "[$env] Private upload bucket"
  exists gcloud storage buckets describe "gs://$BUCKET" ||
    gcloud storage buckets create "gs://$BUCKET" --location="$REGION" \
      --uniform-bucket-level-access --public-access-prevention
  # Storage tiering: ไฟล์แนบของคำร้องที่ปิดแล้วแทบไม่ถูกเปิดอีก จึงย้ายไป class ที่ถูกกว่า
  local lifecycle
  lifecycle=$(mktemp)
  cat >"$lifecycle" <<'JSON'
{"rule": [
  {"action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
   "condition": {"age": 30, "matchesStorageClass": ["STANDARD"]}},
  {"action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
   "condition": {"age": 180, "matchesStorageClass": ["NEARLINE"]}}
]}
JSON
  gcloud storage buckets update "gs://$BUCKET" --lifecycle-file="$lifecycle"
  rm -f "$lifecycle"

  log "[$env] Public web bucket (React static files)"
  if ! exists gcloud storage buckets describe "gs://$WEB_BUCKET"; then
    gcloud storage buckets create "gs://$WEB_BUCKET" --location="$REGION" \
      --uniform-bucket-level-access
    gcloud storage buckets update "gs://$WEB_BUCKET" \
      --web-main-page-suffix=index.html --web-error-page=index.html
  fi
  gcloud storage buckets add-iam-policy-binding "gs://$WEB_BUCKET" \
    --member=allUsers --role=roles/storage.objectViewer >/dev/null
  # GitHub Actions อัปโหลดไฟล์ build ของ frontend ได้เฉพาะ bucket นี้
  gcloud storage buckets add-iam-policy-binding "gs://$WEB_BUCKET" \
    --member="serviceAccount:$DEPLOYER_SA" --role=roles/storage.objectAdmin >/dev/null

  log "[$env] Runtime service account (least privilege)"
  exists gcloud iam service-accounts describe "$API_SA" ||
    gcloud iam service-accounts create "$API_SA_NAME" --display-name="Smart Campus API ($env)"
  for s in "$SECRET_DB" "$SECRET_JWT"; do
    gcloud secrets add-iam-policy-binding "$s" --member="serviceAccount:$API_SA" \
      --role=roles/secretmanager.secretAccessor >/dev/null
  done
  gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
    --member="serviceAccount:$API_SA" --role=roles/storage.objectUser >/dev/null
  # เซ็น Signed URL ผ่าน IAM signBlob ด้วยตัวเอง
  gcloud iam service-accounts add-iam-policy-binding "$API_SA" \
    --member="serviceAccount:$API_SA" --role=roles/iam.serviceAccountTokenCreator >/dev/null
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --condition=None \
    --member="serviceAccount:$API_SA" --role=roles/cloudsql.client >/dev/null
  # ให้ GitHub deploy โดยใช้ SA นี้ได้
  gcloud iam service-accounts add-iam-policy-binding "$API_SA" \
    --member="serviceAccount:$DEPLOYER_SA" --role=roles/iam.serviceAccountUser >/dev/null

  log "[$env] Bootstrap image"
  local image="$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/api:init"
  if ! exists gcloud artifacts docker images describe "$image"; then
    gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
    docker build --target production -t "$image" "$(dirname "$0")/../../backend"
    docker push "$image"
  fi

  # ^@^ = ใช้ @ เป็นตัวคั่นแทน comma เพราะ CORS_ORIGINS/ALLOWED_HOSTS มี comma
  local envs="^@^ENVIRONMENT=$APP_ENV@DEBUG=false@POSTGRES_SERVER=$db_host@POSTGRES_PORT=5432"
  envs+="@POSTGRES_USER=$DB_USER@POSTGRES_DB=$DB_NAME@DB_SSL=require@DB_POOL_SIZE=3@DB_MAX_OVERFLOW=2@DB_POOL_TIMEOUT=10"
  envs+="@STORAGE_PROVIDER=gcs@GCS_BUCKET_NAME=$BUCKET@GCS_PROJECT_ID=$PROJECT_ID"
  envs+="@CORS_ORIGINS=$frontend_origin@ALLOWED_HOSTS=*.run.app"
  envs+="@LOG_LEVEL=INFO@LOG_FORMAT=json@GCP_PROJECT_ID=$PROJECT_ID"
  local secrets="POSTGRES_PASSWORD=$SECRET_DB:latest,SECRET_KEY=$SECRET_JWT:latest"
  local net=(--network="$VPC" --subnet="$SUBNET" --vpc-egress=private-ranges-only)

  log "[$env] Migration job $MIGRATE_JOB"
  # รันซ้ำ: อัปเดตแค่ config ไม่แตะ image (ไม่งั้นจะย้อนกลับไปใช้ :init ที่ไม่รู้จัก migration ใหม่)
  if exists gcloud run jobs describe "$MIGRATE_JOB" --region="$REGION"; then
    gcloud run jobs update "$MIGRATE_JOB" --region="$REGION" \
      --set-env-vars="$envs" --set-secrets="$secrets"
  else
    gcloud run jobs create "$MIGRATE_JOB" --region="$REGION" --image="$image" \
      --service-account="$API_SA" "${net[@]}" --set-env-vars="$envs" --set-secrets="$secrets" \
      --command=alembic --args=upgrade,head --max-retries=0 --task-timeout=300
  fi
  gcloud run jobs execute "$MIGRATE_JOB" --region="$REGION" --wait

  log "[$env] Seed job $SEED_JOB (รันด้วยมือผ่าน ./setup.sh seed)"
  if ! exists gcloud run jobs describe "$SEED_JOB" --region="$REGION"; then
    gcloud run jobs create "$SEED_JOB" --region="$REGION" --image="$image" \
      --service-account="$API_SA" "${net[@]}" --set-env-vars="$envs" --set-secrets="$secrets" \
      --command=python --args=seed.py --max-retries=0 --task-timeout=300
  fi

  log "[$env] Cloud Run service $SERVICE"
  local svc_flags=(--region="$REGION" --service-account="$API_SA" "${net[@]}"
    --set-env-vars="$envs" --set-secrets="$secrets"
    --cpu=1 --memory=512Mi --min-instances=0 --max-instances="$MAX_INSTANCES"
    --concurrency=20 --cpu-throttling \
    --startup-probe="$STARTUP_PROBE")
  if exists gcloud run services describe "$SERVICE" --region="$REGION"; then
    # รันซ้ำ: คง image ที่ CD deploy ไว้
    gcloud run services update "$SERVICE" "${svc_flags[@]}"
  else
    gcloud run deploy "$SERVICE" --image="$image" "${svc_flags[@]}" --allow-unauthenticated
  fi
  log "[$env] Deployer IAM is limited to this environment's Cloud Run resources"
  ensure_deployer "$DEPLOYER_SA"
  gcloud run services add-iam-policy-binding "$SERVICE" --region="$REGION" \
    --member="serviceAccount:$DEPLOYER_SA" --role=roles/run.developer >/dev/null
  gcloud run jobs add-iam-policy-binding "$MIGRATE_JOB" --region="$REGION" \
    --member="serviceAccount:$DEPLOYER_SA" --role=roles/run.developer >/dev/null
  gcloud run jobs add-iam-policy-binding "$SEED_JOB" --region="$REGION" \
    --member="serviceAccount:$DEPLOYER_SA" --role=roles/run.developer >/dev/null
  if [ "$env" = "prod" ]; then
    # สิทธิ์กว้างจากเวอร์ชันเก่า: run.developer ทั้ง project และ WIF ที่เชื่อทั้ง repo
    local project_number
    project_number=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
    gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:$PROD_DEPLOYER_SA" --role=roles/run.developer \
      --condition=None --quiet >/dev/null 2>&1 || true
    gcloud iam service-accounts remove-iam-policy-binding "$PROD_DEPLOYER_SA" \
      --role=roles/iam.workloadIdentityUser \
      --member="principalSet://iam.googleapis.com/projects/${project_number}/locations/global/workloadIdentityPools/github/attribute.repository/${REPO}" \
      --quiet >/dev/null 2>&1 || true
  fi

  log "[$env] GitHub Environment '$env' variables"
  local api_url
  api_url=$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')
  echo "  SERVICE_NAME = $SERVICE"
  echo "  MIGRATE_JOB  = $MIGRATE_JOB"
  echo "  DEPLOYER_SA  = $DEPLOYER_SA"
  echo "  WEB_BUCKET   = $WEB_BUCKET"
  echo "  API_BASE_URL = $api_url/api/v1"
  echo "  CORS origin  = $frontend_origin"
  echo "  Frontend URL = https://$WEB_BUCKET.storage.googleapis.com/index.html"
  echo "  (open index.html — the bucket root does not serve the website config over HTTPS)"
}

seed() {
  local env=$1 admin_email=${2:?admin email required}
  if [ "$env" = "prod" ] && [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
    echo "SEED_DEMO_DATA=true is refused for prod (demo account passwords are public)." >&2
    exit 1
  fi
  env_names "$env"
  local secret="seed-admin-password${SUFFIX}"
  if ! exists gcloud secrets describe "$secret"; then
    read -r -s -p "Initial admin password (>= 12 chars): " admin_pass; echo
    printf '%s' "$admin_pass" | gcloud secrets create "$secret" --data-file=- \
      --replication-policy=user-managed --locations="$REGION"
    unset admin_pass
    gcloud secrets add-iam-policy-binding "$secret" --member="serviceAccount:$API_SA" \
      --role=roles/secretmanager.secretAccessor >/dev/null
  fi
  gcloud run jobs update "$SEED_JOB" --region="$REGION" \
    --update-env-vars="SEED_ADMIN_EMAIL=$admin_email,SEED_DEMO_DATA=${SEED_DEMO_DATA:-false}" \
    --update-secrets="SEED_ADMIN_PASSWORD=$secret:latest"
  gcloud run jobs execute "$SEED_JOB" --region="$REGION" --wait
  echo "เปลี่ยนรหัสผ่าน admin หลัง login ครั้งแรก แล้วลบ secret: gcloud secrets delete $secret"
}

dashboard() {
  env_names "${1:?prod|dev}"
  local name="Smart Campus - $SERVICE"
  if [ -n "$(gcloud monitoring dashboards list --filter="displayName=\"$name\"" --format='value(name)')" ]; then
    echo "dashboard '$name' already exists"
    return
  fi
  local file
  file=$(mktemp)
  sed -e "s|__SERVICE__|$SERVICE|g" -e "s|__PROJECT__|$PROJECT_ID|g" \
    -e "s|__SQL_INSTANCE__|$SQL_INSTANCE|g" -e "s|__TITLE__|$name|g" \
    "$(dirname "$0")/monitoring/dashboard.json" >"$file"
  gcloud monitoring dashboards create --config-from-file="$file"
  rm -f "$file"
  echo "เปิดดูที่ Console > Monitoring > Dashboards > $name"
}

budget() {
  local billing=${1:?billing account id required}
  gcloud billing budgets create --billing-account="$billing" --display-name="smart-campus-300" \
    --budget-amount=300USD --threshold-rule=percent=0.5 --threshold-rule=percent=0.75 \
    --threshold-rule=percent=0.9 --threshold-rule=percent=1.0,basis=forecasted-spend
  gcloud billing budgets create --billing-account="$billing" --display-name="smart-campus-monthly-20" \
    --budget-amount=20USD --calendar-period=month --threshold-rule=percent=0.9
}

case "${1:-}" in
  shared) shared ;;
  env) env_setup "${2:?prod|dev}" "${3:-}" ;;
  seed) env_names "${2:?prod|dev}"; seed "$2" "${3:-}" ;;
  dashboard) dashboard "${2:-}" ;;
  budget) budget "${2:-}" ;;
  *) sed -n '2,22p' "$0"; exit 1 ;;
esac
