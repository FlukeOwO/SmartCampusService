#!/usr/bin/env bash
# =============================================================================
# Smart Campus - one-time GCP setup (Cloud Run + Cloud SQL private IP + GCS)
#
# รันใน Cloud Shell โดยคนที่เป็น Owner ของ project:
#   export PROJECT_ID=smart-campus-prod
#   ./setup.sh shared                 # VPC, PSA, Cloud SQL, Artifact Registry, WIF, deployer SA
#   ./setup.sh env prod https://<frontend-domain>
#   ./setup.sh env dev  https://<frontend-dev-domain>
#   ./setup.sh seed prod admin@your-university.ac.th   # สร้างบัญชี admin คนแรก (ครั้งเดียว)
#   ./setup.sh budget <BILLING_ACCOUNT_ID>
#
# รันซ้ำได้: resource ที่มีอยู่แล้วจะถูกข้าม
# =============================================================================
set -euo pipefail

: "${PROJECT_ID:?export PROJECT_ID first}"
REGION="${REGION:-asia-southeast1}"
REPO="${REPO:-FlukeOwO/SmartCampusService}"

VPC=campus-vpc
SUBNET=campus-run-subnet
SUBNET_RANGE=10.10.0.0/24
PSA_RANGE_NAME=campus-psa-range
PSA_RANGE_START=10.20.0.0
SQL_INSTANCE=campus-db
AR_REPO=campus
DEPLOYER_SA="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
exists() { "$@" >/dev/null 2>&1; }

gcloud config set project "$PROJECT_ID" >/dev/null

# -----------------------------------------------------------------------------
shared() {
  log "1) Enable APIs"
  gcloud services enable run.googleapis.com sqladmin.googleapis.com compute.googleapis.com \
    servicenetworking.googleapis.com artifactregistry.googleapis.com \
    secretmanager.googleapis.com iam.googleapis.com iamcredentials.googleapis.com \
    sts.googleapis.com storage.googleapis.com

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
      --maintenance-window-day=SAT --maintenance-window-hour=20 \
      --ssl-mode=ENCRYPTED_ONLY

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

  log "6) GitHub deployer service account"
  exists gcloud iam service-accounts describe "$DEPLOYER_SA" ||
    gcloud iam service-accounts create github-deployer --display-name="GitHub Actions deployer"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --condition=None \
    --member="serviceAccount:$DEPLOYER_SA" --role=roles/run.developer >/dev/null
  gcloud artifacts repositories add-iam-policy-binding "$AR_REPO" --location="$REGION" \
    --member="serviceAccount:$DEPLOYER_SA" --role=roles/artifactregistry.writer >/dev/null

  log "7) Workload Identity Federation (GitHub OIDC, this repo only)"
  local project_number
  project_number=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
  exists gcloud iam workload-identity-pools describe github --location=global ||
    gcloud iam workload-identity-pools create github --location=global --display-name="GitHub"
  exists gcloud iam workload-identity-pools providers describe smart-campus \
    --location=global --workload-identity-pool=github ||
    gcloud iam workload-identity-pools providers create-oidc smart-campus --location=global \
      --workload-identity-pool=github --issuer-uri="https://token.actions.githubusercontent.com" \
      --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
      --attribute-condition="assertion.repository == '$REPO'"
  gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA" \
    --role=roles/iam.workloadIdentityUser \
    --member="principalSet://iam.googleapis.com/projects/$project_number/locations/global/workloadIdentityPools/github/attribute.repository/$REPO" \
    >/dev/null

  log "Done. GitHub Environment variables (dev + prod):"
  echo "  GCP_PROJECT_ID = $PROJECT_ID"
  echo "  GCP_REGION     = $REGION"
  echo "  WIF_PROVIDER   = projects/$project_number/locations/global/workloadIdentityPools/github/providers/smart-campus"
  echo "  DEPLOYER_SA    = $DEPLOYER_SA"
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
  SERVICE="campus-api${SUFFIX}"
  MIGRATE_JOB="campus-migrate${SUFFIX}"
  SEED_JOB="campus-seed${SUFFIX}"
  API_SA_NAME="campus-api${SUFFIX}-sa"
  API_SA="${API_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
  BUCKET="${PROJECT_ID}-campus-uploads${SUFFIX}"
  SECRET_DB="db-password${SUFFIX}"
  SECRET_JWT="jwt-secret-key${SUFFIX}"
}

env_setup() {
  local env=$1 frontend_origin=${2:?frontend origin required, e.g. https://campus.example.com}
  env_names "$env"
  local db_host
  db_host=$(gcloud sql instances describe "$SQL_INSTANCE" --format='value(ipAddresses[0].ipAddress)')

  log "[$env] Database + user"
  exists gcloud sql databases describe "$DB_NAME" --instance="$SQL_INSTANCE" ||
    gcloud sql databases create "$DB_NAME" --instance="$SQL_INSTANCE"
  if ! exists gcloud secrets describe "$SECRET_DB"; then
    local db_pass
    db_pass=$(openssl rand -base64 24 | tr -d '/+=')
    gcloud sql users create "$DB_USER" --instance="$SQL_INSTANCE" --password="$db_pass"
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
  envs+="@POSTGRES_USER=$DB_USER@POSTGRES_DB=$DB_NAME@DB_SSL=require@DB_POOL_SIZE=3@DB_MAX_OVERFLOW=2"
  envs+="@STORAGE_PROVIDER=gcs@GCS_BUCKET_NAME=$BUCKET@GCS_PROJECT_ID=$PROJECT_ID"
  envs+="@CORS_ORIGINS=$frontend_origin@ALLOWED_HOSTS=*.run.app"
  envs+="@LOG_LEVEL=INFO@LOG_FORMAT=json"
  local secrets="POSTGRES_PASSWORD=$SECRET_DB:latest,SECRET_KEY=$SECRET_JWT:latest"
  local net=(--network="$VPC" --subnet="$SUBNET" --vpc-egress=private-ranges-only)

  log "[$env] Migration job $MIGRATE_JOB"
  if exists gcloud run jobs describe "$MIGRATE_JOB" --region="$REGION"; then
    gcloud run jobs update "$MIGRATE_JOB" --region="$REGION" --image="$image" \
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
  gcloud run deploy "$SERVICE" --region="$REGION" --image="$image" \
    --service-account="$API_SA" "${net[@]}" \
    --set-env-vars="$envs" --set-secrets="$secrets" \
    --cpu=1 --memory=512Mi --min-instances=0 --max-instances="$MAX_INSTANCES" \
    --concurrency=80 --cpu-throttling --allow-unauthenticated
  echo "ตั้ง startup probe: Console > Cloud Run > $SERVICE > Edit > Health checks > HTTP GET /healthz"

  log "[$env] GitHub Environment '$env' variables"
  echo "  SERVICE_NAME = $SERVICE"
  echo "  MIGRATE_JOB  = $MIGRATE_JOB"
  echo "  API URL      = $(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
}

seed() {
  local env=$1 admin_email=${2:?admin email required}
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

budget() {
  local billing=${1:?billing account id required}
  gcloud billing budgets create --billing-account="$billing" --display-name="smart-campus-300" \
    --budget-amount=300USD --threshold-rule=percent=0.5 --threshold-rule=percent=0.75 \
    --threshold-rule=percent=0.9
  gcloud billing budgets create --billing-account="$billing" --display-name="smart-campus-monthly-20" \
    --budget-amount=20USD --calendar-period=month --threshold-rule=percent=0.9
}

case "${1:-}" in
  shared) shared ;;
  env) env_setup "${2:?prod|dev}" "${3:-}" ;;
  seed) env_names "${2:?prod|dev}"; seed "$2" "${3:-}" ;;
  budget) budget "${2:-}" ;;
  *) sed -n '2,16p' "$0"; exit 1 ;;
esac
