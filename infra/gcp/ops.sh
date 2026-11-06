#!/usr/bin/env bash
# =============================================================================
# Smart Campus - งานดูแลระบบหลังติดตั้ง (รันใน Cloud Shell)
#
#   export PROJECT_ID=smart-campus-prod
#   ./ops.sh status   prod            # revision ที่รับ traffic + สถานะ Cloud SQL
#   ./ops.sh canary   prod 10         # ส่ง 10% ไป revision ล่าสุด (ที่เหลือคง revision เดิม)
#   ./ops.sh promote  prod            # revision ล่าสุดรับ 100%
#   ./ops.sh rollback prod [REVISION] # กลับไป revision ก่อนหน้า (หรือที่ระบุ) 100%
#   ./ops.sh db-ha    on|off          # เปิด/ปิด Cloud SQL High Availability (2 zone)
#   ./ops.sh db-stop | db-start       # หยุด/เปิด Cloud SQL ช่วงไม่ใช้งาน (ประหยัดค่า compute)
#   ./ops.sh teardown                 # ลบทั้ง project หลังจบรายวิชา
# =============================================================================
set -euo pipefail

: "${PROJECT_ID:?export PROJECT_ID first}"
REGION="${REGION:-asia-southeast1}"
SQL_INSTANCE=campus-db
# HA ใช้กับ shared-core (db-f1-micro) ไม่ได้ ต้องเป็น dedicated core
HA_TIER="${HA_TIER:-db-custom-1-3840}"
BASE_TIER="${BASE_TIER:-db-f1-micro}"

gcloud config set project "$PROJECT_ID" >/dev/null

service_name() {
  case "${1:?prod|dev}" in
    prod) echo campus-api ;;
    dev) echo campus-api-dev ;;
    *) echo "env must be prod or dev" >&2; exit 1 ;;
  esac
}

confirm() {
  read -r -p "$1 [y/N] " answer
  [ "$answer" = "y" ] || { echo "cancelled"; exit 1; }
}

latest_revision() {
  gcloud run services describe "$1" --region="$REGION" \
    --format='value(status.latestCreatedRevisionName)'
}

case "${1:-}" in
  status)
    svc=$(service_name "${2:-}")
    gcloud run services describe "$svc" --region="$REGION" \
      --format='table(status.traffic[].revisionName,status.traffic[].percent,status.traffic[].tag)'
    gcloud run revisions list --service="$svc" --region="$REGION" --limit=5
    gcloud sql instances describe "$SQL_INSTANCE" \
      --format='table(state,settings.tier,settings.availabilityType,settings.activationPolicy)'
    ;;
  canary)
    svc=$(service_name "${2:-}")
    pct=${3:?percent, e.g. 10}
    rev=$(latest_revision "$svc")
    # revision อื่นได้ traffic ที่เหลือตามสัดส่วนเดิม
    gcloud run services update-traffic "$svc" --region="$REGION" --to-revisions="$rev=$pct"
    ;;
  promote)
    svc=$(service_name "${2:-}")
    gcloud run services update-traffic "$svc" --region="$REGION" \
      --to-revisions="$(latest_revision "$svc")=100"
    ;;
  rollback)
    svc=$(service_name "${2:-}")
    rev=${3:-}
    if [ -z "$rev" ]; then
      # revision ที่สร้างก่อนตัวล่าสุด
      rev=$(gcloud run revisions list --service="$svc" --region="$REGION" \
        --sort-by=~metadata.creationTimestamp --format='value(metadata.name)' --limit=2 | tail -n1)
    fi
    confirm "Send 100% traffic of $svc to $rev?"
    gcloud run services update-traffic "$svc" --region="$REGION" --to-revisions="$rev=100"
    ;;
  db-ha)
    case "${2:-}" in
      on)
        echo "Cloud SQL จะ restart สั้น ๆ และค่าใช้จ่ายเพิ่มขึ้นมาก (tier $HA_TIER x 2 zone)"
        confirm "Enable REGIONAL availability on $SQL_INSTANCE?"
        gcloud sql instances patch "$SQL_INSTANCE" --tier="$HA_TIER" --availability-type=REGIONAL
        ;;
      off)
        confirm "Return $SQL_INSTANCE to ZONAL $BASE_TIER?"
        gcloud sql instances patch "$SQL_INSTANCE" --availability-type=ZONAL --tier="$BASE_TIER"
        ;;
      *) echo "usage: ./ops.sh db-ha on|off" >&2; exit 1 ;;
    esac
    ;;
  db-stop)
    gcloud sql instances patch "$SQL_INSTANCE" --activation-policy=NEVER
    echo "ยังเสียค่า storage อยู่ เปิดคืนด้วย ./ops.sh db-start"
    ;;
  db-start)
    gcloud sql instances patch "$SQL_INSTANCE" --activation-policy=ALWAYS
    ;;
  teardown)
    echo "ลบ project $PROJECT_ID ทั้งหมด (Cloud Run, Cloud SQL, buckets, secrets) - กู้คืนได้ภายใน 30 วัน"
    read -r -p "Type the project id to confirm: " typed
    [ "$typed" = "$PROJECT_ID" ] || { echo "cancelled"; exit 1; }
    gcloud projects delete "$PROJECT_ID"
    ;;
  *)
    sed -n '2,14p' "$0"
    exit 1
    ;;
esac
