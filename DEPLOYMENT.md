# Smart Campus Service Platform - Deployment Guide

## 📋 Table of Contents

- [Local Development](#local-development)
- [Production Testing](#production-testing)
- [Google Cloud Platform Deployment](#google-cloud-platform-deployment)
- [Environment Variables](#environment-variables)
- [Database Migration](#database-migration)

---

## 🚀 Local Development

### Prerequisites

- Docker Desktop (Windows/Mac) หรือ Docker Engine (Linux)
- Docker Compose v2+
- Git

### Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd SmartCampusService

# 2. Copy environment file
cp .env.example .env

# 3. Edit .env file (ถ้าต้องการปรับแต่ง)
# vim .env

# 4. Start all services
docker-compose up -d

# 5. Check services status
docker-compose ps

# 6. Run database migrations
docker-compose exec backend alembic upgrade head

# 7. Seed initial data
docker-compose exec backend python seed.py

# 8. Access services
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/api/v1/docs
```

### Development Commands

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart service
docker-compose restart backend

# Stop all services
docker-compose down

# Remove all data (including database)
docker-compose down -v

# Rebuild images
docker-compose build --no-cache

# Execute command in container
docker-compose exec backend bash
docker-compose exec backend python seed.py
docker-compose exec backend alembic revision --autogenerate -m "description"
```

---

## 🔨 Production Testing (Local)

ทดสอบ Production build บน localhost:

```bash
# Build and run production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build

# Access
# - Frontend: http://localhost (port 80)
# - Backend: http://localhost:8000
```

---

## ☁️ Google Cloud Platform Deployment

### Architecture Overview

```
[Cloud CDN] → [Load Balancer] → [Cloud Storage (Frontend)]
                              → [Cloud Run (Backend)] → [Cloud SQL]
                                                      → [Cloud Storage (Files)]
```

### Prerequisites

1. GCP Project with billing enabled
2. `gcloud` CLI installed and authenticated
3. Required APIs enabled:
   - Cloud Run API
   - Cloud SQL Admin API
   - Cloud Storage API
   - Container Registry API
   - Cloud Build API

### Step-by-Step Deployment

#### 1. Enable Required APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable vpcaccess.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

#### 2. Set Environment Variables

```bash
export PROJECT_ID="your-project-id"
export REGION="asia-southeast1"
export DB_INSTANCE_NAME="campus-db"
export DB_PASSWORD="your-secure-password"
export JWT_SECRET="your-jwt-secret-key"
```

#### 3. Create Cloud SQL Instance

```bash
# Create PostgreSQL instance
gcloud sql instances create $DB_INSTANCE_NAME \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --root-password=$DB_PASSWORD

# Create database
gcloud sql databases create smart_campus \
  --instance=$DB_INSTANCE_NAME

# Create user
gcloud sql users create campus_admin \
  --instance=$DB_INSTANCE_NAME \
  --password=$DB_PASSWORD
```

#### 4. Create Cloud Storage Buckets

```bash
# Bucket for uploaded files
gsutil mb -l $REGION gs://${PROJECT_ID}-campus-uploads

# Make bucket private (use signed URLs)
gsutil iam ch allUsers:objectViewer gs://${PROJECT_ID}-campus-uploads

# Bucket for frontend (optional)
gsutil mb -l $REGION gs://${PROJECT_ID}-campus-frontend
gsutil web set -m index.html -e index.html gs://${PROJECT_ID}-campus-frontend
```

#### 5. Create Secrets in Secret Manager

```bash
# JWT Secret
echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret-key --data-file=-

# Database Password
echo -n "$DB_PASSWORD" | gcloud secrets create db-password --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding jwt-secret-key \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### 6. Create VPC Connector (for Cloud SQL access)

```bash
gcloud compute networks vpc-access connectors create campus-vpc-connector \
  --region=$REGION \
  --range=10.8.0.0/28
```

#### 7. Build and Push Backend Image

```bash
cd backend

# Build production image
docker build --target production -t gcr.io/$PROJECT_ID/campus-backend:latest .

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/campus-backend:latest
```

#### 8. Deploy Backend to Cloud Run

```bash
gcloud run deploy campus-backend \
  --image=gcr.io/$PROJECT_ID/campus-backend:latest \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="\
ENVIRONMENT=production,\
STORAGE_PROVIDER=gcs,\
GCS_BUCKET_NAME=${PROJECT_ID}-campus-uploads,\
GCS_PROJECT_ID=${PROJECT_ID},\
POSTGRES_SERVER=/cloudsql/${PROJECT_ID}:${REGION}:${DB_INSTANCE_NAME},\
POSTGRES_DB=smart_campus,\
POSTGRES_USER=campus_admin" \
  --set-secrets="SECRET_KEY=jwt-secret-key:latest,POSTGRES_PASSWORD=db-password:latest" \
  --vpc-connector=campus-vpc-connector \
  --add-cloudsql-instances=${PROJECT_ID}:${REGION}:${DB_INSTANCE_NAME}

# Get backend URL
export BACKEND_URL=$(gcloud run services describe campus-backend --region=$REGION --format='value(status.url)')
echo "Backend URL: $BACKEND_URL"
```

#### 9. Run Database Migrations (Cloud Run Job)

```bash
# Create migration job
gcloud run jobs create campus-db-migrate \
  --image=gcr.io/$PROJECT_ID/campus-backend:latest \
  --region=$REGION \
  --set-env-vars="POSTGRES_SERVER=/cloudsql/${PROJECT_ID}:${REGION}:${DB_INSTANCE_NAME}" \
  --set-secrets="POSTGRES_PASSWORD=db-password:latest" \
  --add-cloudsql-instances=${PROJECT_ID}:${REGION}:${DB_INSTANCE_NAME} \
  --vpc-connector=campus-vpc-connector \
  --command="alembic" \
  --args="upgrade,head"

# Execute migration
gcloud run jobs execute campus-db-migrate --region=$REGION --wait
```

#### 10. Build and Deploy Frontend

```bash
cd ../frontend

# Build static files
docker build --target builder \
  --build-arg VITE_API_BASE_URL=$BACKEND_URL/api/v1 \
  -o dist .

# Upload to Cloud Storage
gsutil -m cp -r dist/* gs://${PROJECT_ID}-campus-frontend/

# Set up Cloud CDN (optional)
# Follow: https://cloud.google.com/cdn/docs/setting-up-cdn-with-bucket
```

---

## 🔧 Environment Variables

### Development (.env)

```env
ENVIRONMENT=development
DEBUG=true
STORAGE_PROVIDER=local
POSTGRES_SERVER=db
```

### Production (Cloud Run)

```env
ENVIRONMENT=production
DEBUG=false
STORAGE_PROVIDER=gcs
GCS_BUCKET_NAME=project-campus-uploads
GCS_PROJECT_ID=your-project-id
POSTGRES_SERVER=/cloudsql/project:region:instance
```

---

## 🗄️ Database Migration

### Local Development

```bash
# Create migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Run migrations
docker-compose exec backend alembic upgrade head

# Rollback
docker-compose exec backend alembic downgrade -1
```

### Production (Cloud Run)

```bash
# Execute migration job
gcloud run jobs execute campus-db-migrate --region=$REGION --wait

# Or via Cloud SQL Proxy
cloud_sql_proxy -instances=$PROJECT_ID:$REGION:$DB_INSTANCE_NAME=tcp:5432 &
POSTGRES_SERVER=localhost alembic upgrade head
```

---

## 📊 Monitoring & Logging

### Cloud Logging

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=campus-backend" --limit 50

# Real-time logs
gcloud run services logs tail campus-backend --region=$REGION
```

### Cloud Monitoring

Access metrics in GCP Console:
- Cloud Run → campus-backend → Metrics
- Monitor: Request count, Latency, Error rate, Memory usage

---

## 🔒 Security Best Practices

1. ✅ Use Secret Manager for sensitive data
2. ✅ Enable HTTPS only (Cloud Run default)
3. ✅ Use Service Account with minimal permissions
4. ✅ Enable VPC for database access
5. ✅ Regular security updates (base images)
6. ✅ Implement rate limiting
7. ✅ Use Cloud Armor for DDoS protection

---

## 💰 Cost Optimization

1. Set min-instances=0 (scale to zero when idle)
2. Use appropriate instance sizes
3. Enable request-based autoscaling
4. Use Cloud CDN for static assets
5. Implement caching strategies
6. Monitor and set budget alerts

---

## 🆘 Troubleshooting

### Backend not starting

```bash
# Check logs
gcloud run services logs tail campus-backend --region=$REGION

# Check environment variables
gcloud run services describe campus-backend --region=$REGION

# Test database connection
gcloud sql connect $DB_INSTANCE_NAME --user=campus_admin
```

### Database connection issues

```bash
# Verify VPC connector
gcloud compute networks vpc-access connectors describe campus-vpc-connector --region=$REGION

# Check Cloud SQL instance
gcloud sql instances describe $DB_INSTANCE_NAME
```

---

## 📚 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/deployment/)
- [Docker Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
