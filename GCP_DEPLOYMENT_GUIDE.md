# MantleIQ GCP Deployment Guide

Complete infrastructure-as-code deployment guide for MantleIQ natural hydrogen prospectivity discovery engine on Google Cloud Platform.

**Last Updated:** 2026-05-10  
**Status:** Production Ready  
**Infrastructure:** Terraform IaC

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Initial Setup](#initial-setup)
4. [Deployment Steps](#deployment-steps)
5. [Post-Deployment Configuration](#post-deployment-configuration)
6. [Database Setup](#database-setup)
7. [Docker Image Preparation](#docker-image-preparation)
8. [Running the Pipeline](#running-the-pipeline)
9. [Monitoring & Operations](#monitoring--operations)
10. [Cost Optimization](#cost-optimization)
11. [Troubleshooting](#troubleshooting)
12. [Cleanup](#cleanup)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MantleIQ GCP Architecture                    │
└─────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ Frontend (Optional: Cloud Storage + Cloud CDN)                    │
│  └─ React application hosted on Cloud Storage with CDN caching   │
└────────────────────────────────────────────────────────────────────┘
                                    ↓
                      ┌──────────────────────────┐
                      │   Cloud Run Backend      │
                      │  (FastAPI + Python)      │
                      │  - Auto-scaling: 0-100   │
                      │  - 2 CPU, 2GB RAM        │
                      └──────────────────────────┘
                                    ↓
          ┌─────────────────────────────────────────────────┐
          │ VPC Access Connector (Private Network Access)   │
          └─────────────────────────────────────────────────┘
                                    ↓
    ┌──────────────────────────────────────────────────────────┐
    │        Cloud SQL (PostgreSQL 15 + PostGIS 3.4)          │
    │  - 4-CPU, 16GB RAM custom machine                        │
    │  - HA enabled (Regional replication)                     │
    │  - SSD storage (100GB, auto-scaling)                     │
    │  - Automated backups + point-in-time recovery           │
    └──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Cloud Storage Buckets                     │
├──────────────────────────────────────────────────────────────┤
│ • raw/       - Downloaded geospatial data (auto-delete 90d) │
│ • curated/   - Processed GeoTIFFs, normalized data (versioned)
│ • reports/   - PDF exports + analysis results (versioned)   │
│ • tiles/     - Vector tiles for web rendering               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                  Cloud Scheduler + Cloud Pub/Sub             │
├──────────────────────────────────────────────────────────────┤
│ Daily pipeline execution at 2 AM UTC (configurable)         │
│ Triggers: Data ingestion → Feature computation → Scoring    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│            Cloud Monitoring + Cloud Logging                  │
├──────────────────────────────────────────────────────────────┤
│ • Real-time metrics: Error rate, latency, instance count    │
│ • Alert policies: Page on errors > 5%                       │
│ • Centralized logging: All services, queryable via Logs     │
└──────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Tools

- **Terraform** ≥ 1.0
  ```bash
  # Install on macOS
  brew install terraform
  
  # Verify
  terraform version
  ```

- **Google Cloud SDK**
  ```bash
  # Install on macOS
  brew install google-cloud-sdk
  
  # Verify
  gcloud --version
  ```

- **Docker** (for building container images)
  ```bash
  # Verify
  docker --version
  ```

### GCP Setup

1. **Create GCP Project**
   ```bash
   gcloud projects create mantleiq-prod --name="MantleIQ Production"
   gcloud config set project mantleiq-prod
   ```

2. **Enable Billing**
   - Go to [GCP Console](https://console.cloud.google.com)
   - Select your project
   - Enable billing for the project

3. **Authenticate gcloud**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

4. **Set Default Region**
   ```bash
   gcloud config set compute/region us-central1
   gcloud config set compute/zone us-central1-a
   ```

### Project ID & Configuration

Get your project ID:
```bash
PROJECT_ID=$(gcloud config get-value project)
echo $PROJECT_ID
```

Export for use in deployment:
```bash
export GCP_PROJECT_ID=$PROJECT_ID
```

---

## Initial Setup

### 1. Clone Repository

```bash
cd /path/to/projects
git clone https://github.com/your-org/mantleiq.git
cd mantleiq
```

### 2. Prepare Terraform Configuration

```bash
cd infra/terraform

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Update `terraform.tfvars`:**

```hcl
gcp_project_id        = "your-actual-project-id"
gcp_region            = "us-central1"
database_instance_name = "mantleiq-postgres-prod"
database_machine_type = "db-custom-4-16"
database_user         = "mantleiq_user"
default_basin_id      = "kansas-rift-2024"
pipeline_schedule     = "0 2 * * *"  # 2 AM UTC daily
```

### 3. Initialize Terraform

```bash
# From infra/terraform directory
terraform init

# List resources to be created
terraform plan -out=tfplan

# Review output carefully
cat tfplan | head -50
```

---

## Deployment Steps

### Step 1: Deploy Infrastructure

```bash
# Apply Terraform configuration
terraform apply tfplan

# Takes ~15-20 minutes
# Terraform will create:
# ✓ VPC Network + Subnet
# ✓ Cloud SQL PostgreSQL + PostGIS
# ✓ Cloud Storage Buckets (4x)
# ✓ VPC Access Connector
# ✓ Cloud Run placeholder
# ✓ Cloud Scheduler
# ✓ IAM Service Accounts
# ✓ Firewall Rules
```

### Step 2: Save Terraform Outputs

```bash
# Export outputs to file
terraform output -json > outputs.json

# Save connection string securely
BACKEND_URL=$(terraform output -raw backend_url 2>/dev/null || echo "TBD")
DB_CONN=$(terraform output -raw database_connection_string)

echo "Backend URL: $BACKEND_URL"
echo "Database: See outputs.json"
```

### Step 3: Build & Push Docker Image

```bash
# From project root
cd /path/to/mantleiq

# Set variables
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
IMAGE_NAME="mantleiq-backend"
IMAGE_TAG="latest"
IMAGE_FULL="${REGION}-docker.pkg.dev/${PROJECT_ID}/mantleiq/${IMAGE_NAME}:${IMAGE_TAG}"

# Configure Docker auth
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build image
docker build -f backend/Dockerfile -t ${IMAGE_FULL} .

# Push to Artifact Registry
docker push ${IMAGE_FULL}

# Verify
gcloud artifacts docker images list ${REGION}-docker.pkg.dev/${PROJECT_ID}/mantleiq
```

### Step 4: Deploy Backend to Cloud Run

The Cloud Run service was created by Terraform, but needs the Docker image reference updated.

```bash
gcloud run deploy mantleiq-backend \
  --image=${IMAGE_FULL} \
  --region=${REGION} \
  --platform managed \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 100 \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=postgresql://mantleiq_user:PASSWORD@PRIVATE_IP:5432/mantleiq"
```

**Or update via console:**
1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Select `mantleiq-backend`
3. Click "Edit & Deploy New Revision"
4. Update image to `${IMAGE_FULL}`
5. Save and deploy

---

## Post-Deployment Configuration

### 1. Initialize Database Schema

```bash
# Connect to Cloud SQL via Cloud Shell or Local Cloud SQL Proxy

# Start proxy (in one terminal)
cloud_sql_proxy -instances=PROJECT:REGION:INSTANCE_NAME=tcp:5432 &

# Connect and run schema
psql -h localhost -U mantleiq_user -d mantleiq < infra/sql/001_schema.sql

# Install PostGIS extension
psql -h localhost -U mantleiq_user -d mantleiq -c "CREATE EXTENSION postgis;"

# Verify
psql -h localhost -U mantleiq_user -d mantleiq -c "\dx"
```

### 2. Set Environment Variables in Cloud Run

```bash
gcloud run services update mantleiq-backend \
  --region=us-central1 \
  --update-env-vars=DEBUG=false,LOG_LEVEL=INFO
```

### 3. Configure Cloud Scheduler

The daily pipeline job was created by Terraform. Verify it's enabled:

```bash
gcloud scheduler jobs describe mantleiq-daily-pipeline --location=us-central1

# Enable if needed
gcloud scheduler jobs resume mantleiq-daily-pipeline --location=us-central1

# Test manual execution
gcloud scheduler jobs run mantleiq-daily-pipeline --location=us-central1
```

### 4. Set Up Monitoring Alerts

```bash
# View alert policies
gcloud alpha monitoring policies list

# Create custom notification channel (Email)
# Via Cloud Console → Monitoring → Notification Channels
```

---

## Database Setup

### Connect via Cloud SQL Proxy

**Local Machine:**
```bash
cloud_sql_proxy -instances=PROJECT_ID:REGION:INSTANCE_NAME=tcp:5432

# In another terminal
psql -h localhost -U mantleiq_user -d mantleiq
```

**Cloud Shell:**
```bash
gcloud sql connect mantleiq-postgres --user=mantleiq_user
```

### Import Initial Data

```bash
# Create test basin
psql -h localhost -U mantleiq_user -d mantleiq << EOF
INSERT INTO basins (id, name, region, country)
VALUES (
  gen_random_uuid(),
  'Kansas Rift',
  'Kansas, USA',
  'United States'
);
EOF

# Verify
psql -h localhost -U mantleiq_user -d mantleiq -c "SELECT * FROM basins;"
```

### Enable PostGIS

```bash
# Login to database
psql -h localhost -U mantleiq_user -d mantleiq

# Enable extension
CREATE EXTENSION IF NOT EXISTS postgis;

# Verify
SELECT PostGIS_version();
```

---

## Docker Image Preparation

### Build for Production

```bash
# From project root
docker build -f backend/Dockerfile \
  -t mantleiq-backend:latest \
  -t mantleiq-backend:v1.0.0 \
  --build-arg ENVIRONMENT=production \
  .
```

### Push to Artifact Registry

```bash
docker push us-central1-docker.pkg.dev/PROJECT_ID/mantleiq/mantleiq-backend:latest
docker push us-central1-docker.pkg.dev/PROJECT_ID/mantleiq/mantleiq-backend:v1.0.0
```

### Verify Image

```bash
gcloud artifacts docker images list us-central1-docker.pkg.dev/PROJECT_ID/mantleiq
gcloud artifacts docker images describe us-central1-docker.pkg.dev/PROJECT_ID/mantleiq/mantleiq-backend
```

---

## Running the Pipeline

### Manual Execution (Testing)

```bash
# Trigger via API endpoint
curl -X POST \
  https://mantleiq-backend-XXXXX.run.app/run-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "basin_id": "kansas-rift-2024",
    "mode": "standard"
  }'

# Check job status
curl https://mantleiq-backend-XXXXX.run.app/job/{job_id}
```

### Automated Daily Execution

Cloud Scheduler runs the pipeline daily at 2 AM UTC. View execution logs:

```bash
# Recent executions
gcloud scheduler jobs describe mantleiq-daily-pipeline \
  --location=us-central1

# Execution logs
gcloud logging read \
  "resource.type=cloud_scheduler_job AND resource.labels.job_id=mantleiq-daily-pipeline" \
  --limit 10
```

### View Pipeline Results

```bash
# List generated reports
gsutil ls gs://mantleiq-prod-reports/

# Download a report
gsutil cp gs://mantleiq-prod-reports/report_2024-05-10.pdf ./
```

---

## Monitoring & Operations

### Cloud Monitoring Dashboard

```bash
# Create custom dashboard (via console)
# Metrics to add:
# - Cloud Run: Requests/sec, Error rate (%), P95 latency
# - Cloud SQL: CPU usage, Memory usage, Disk I/O
# - Storage: Bucket size, Object count
```

### Logs & Debugging

```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mantleiq-backend" \
  --limit 50 --format json | jq '.[] | .timestamp, .jsonPayload.message'

# View Cloud SQL logs
gcloud logging read "resource.type=cloudsql_database AND resource.labels.database_id=PROJECT:mantleiq" \
  --limit 20

# Query logs with filter
gcloud logging read "severity>=ERROR" --limit 10
```

### Performance Monitoring

```bash
# Check Cloud Run metrics
gcloud monitoring time-series list \
  --filter='metric.type=run.googleapis.com/request_count'

# Check Cloud SQL metrics
gcloud monitoring time-series list \
  --filter='resource.type=cloudsql_database'
```

---

## Cost Optimization

### Reduce Cloud SQL Costs

```hcl
# In terraform.tfvars, downgrade for non-prod:
database_machine_type = "db-custom-2-8"  # $120/mo vs $240/mo
cloud_run_max_instances = 10             # Reduced auto-scaling
```

### Use Committed Use Discounts

- Cloud SQL: 1-year commitment = ~25% discount
- Cloud Run: Reserved compute = 25-40% discount

### Auto-scale Cloud Run

Already configured with max_instances=100. Adjust as needed:

```bash
gcloud run services update mantleiq-backend \
  --region=us-central1 \
  --max-instances=50
```

### Enable Cloud Storage Lifecycle Policies

Already configured in Terraform:
- `raw/` bucket: Auto-delete after 90 days
- `reports/` bucket: Auto-delete after 180 days

---

## Troubleshooting

### Cloud Run Won't Start

**Error:** "Image pull failed"

```bash
# Verify image exists and is accessible
gcloud artifacts docker images list us-central1-docker.pkg.dev/PROJECT_ID/mantleiq

# Re-push image
docker push us-central1-docker.pkg.dev/PROJECT_ID/mantleiq/mantleiq-backend:latest

# Update Cloud Run
gcloud run deploy mantleiq-backend \
  --image=us-central1-docker.pkg.dev/PROJECT_ID/mantleiq/mantleiq-backend:latest
```

### Database Connection Failed

**Error:** "could not translate host name"

```bash
# Verify VPC Connector is created
gcloud compute networks vpc-peerings list

# Verify Cloud SQL has private IP
gcloud sql instances describe mantleiq-postgres --format="value(ipAddresses[0].ipAddress)"

# Verify Cloud Run uses connector
gcloud run services describe mantleiq-backend --format='value(spec.template.spec.serviceAccountName)'
```

### Insufficient Quota

**Error:** "Quota exceeded"

```bash
# Check quota usage
gcloud compute project-info describe --project=PROJECT_ID | grep Quota

# Request quota increase via console
# API & Services → Quotas
```

---

## Cleanup

### Destroy All Infrastructure

```bash
# From infra/terraform/
terraform destroy -auto-approve

# Takes ~10-15 minutes
# Removes all GCP resources created by Terraform
```

### Delete Storage Buckets Manually

```bash
# List buckets
gsutil ls

# Delete bucket (if not auto-deleted)
gsutil -m rm -r gs://mantleiq-prod-raw/
```

### Remove Docker Images

```bash
# Delete from Artifact Registry
gcloud artifacts docker images delete us-central1-docker.pkg.dev/PROJECT_ID/mantleiq/mantleiq-backend:latest
```

---

## Quick Reference

### Common Commands

```bash
# Deploy/Update
terraform apply tfplan

# View current state
terraform state list
terraform state show google_sql_database_instance.mantleiq_postgres

# Destroy
terraform destroy -auto-approve

# Check Cloud Run status
gcloud run services describe mantleiq-backend

# View logs
gcloud logging read --limit 10

# Trigger pipeline manually
gcloud scheduler jobs run mantleiq-daily-pipeline
```

### Important URLs

- **Cloud Console:** https://console.cloud.google.com
- **Cloud Run Service:** https://console.cloud.google.com/run
- **Cloud SQL Instances:** https://console.cloud.google.com/sql/instances
- **Cloud Storage:** https://console.cloud.google.com/storage/browser
- **Cloud Logs:** https://console.cloud.google.com/logs/query

### Support & Documentation

- Terraform GCP Provider: https://registry.terraform.io/providers/hashicorp/google/latest
- Cloud Run Docs: https://cloud.google.com/run/docs
- Cloud SQL Docs: https://cloud.google.com/sql/docs
- PostGIS Docs: https://postgis.net/documentation/

---

## Production Checklist

- [ ] GCP project created and billing enabled
- [ ] Terraform variables configured (terraform.tfvars)
- [ ] Infrastructure deployed (terraform apply)
- [ ] Docker image built and pushed to Artifact Registry
- [ ] Cloud Run service deployed with correct image
- [ ] Database schema initialized (001_schema.sql)
- [ ] PostGIS extension installed and verified
- [ ] VPC Connector connectivity tested
- [ ] Cloud Scheduler job enabled and tested
- [ ] Monitoring alerts configured
- [ ] Backup strategy verified (daily, 7-day retention)
- [ ] SSL/TLS certificates configured
- [ ] OAuth 2.0 authentication set up (if needed)
- [ ] Firewall rules reviewed and locked down
- [ ] Cost monitoring dashboard created
- [ ] Runbook and escalation procedures documented

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-10  
**Status:** Production Ready  
**Support:** See SUPPORT.md for contact information
