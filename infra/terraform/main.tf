"""
MantleIQ GCP Deployment - Main Infrastructure
==============================================

This Terraform configuration deploys MantleIQ to Google Cloud Platform with:
- Cloud SQL PostgreSQL 15 + PostGIS 3.4
- Cloud Run for FastAPI backend
- Cloud Storage for data & reports
- Cloud Build for CI/CD
- Monitoring & logging
- VPC networking

Usage:
  terraform init
  terraform plan -out=tfplan
  terraform apply tfplan
  terraform destroy (when done)
"""

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "sqladmin.googleapis.com",      # Cloud SQL
    "run.googleapis.com",             # Cloud Run
    "storage.googleapis.com",         # Cloud Storage
    "cloudbuild.googleapis.com",      # Cloud Build
    "cloudscheduler.googleapis.com",  # Cloud Scheduler
    "monitoring.googleapis.com",      # Cloud Monitoring
    "logging.googleapis.com",         # Cloud Logging
    "artifactregistry.googleapis.com" # Artifact Registry
  ])

  service = each.value
  disable_on_destroy = false
}

# ============================================================================
# NETWORKING
# ============================================================================

resource "google_compute_network" "mantleiq_network" {
  name                    = "mantleiq-network"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [google_project_service.required_apis]
}

resource "google_compute_subnetwork" "mantleiq_subnet" {
  name          = "mantleiq-subnet"
  ip_cidr_range = "10.0.0.0/20"
  region        = var.gcp_region
  network       = google_compute_network.mantleiq_network.id

  depends_on = [google_compute_network.mantleiq_network]
}

resource "google_compute_firewall" "allow_cloudsql_proxy" {
  name    = "allow-cloudsql-proxy"
  network = google_compute_network.mantleiq_network.name

  allow {
    protocol = "tcp"
    ports    = ["5432"]
  }

  source_ranges = ["10.0.0.0/20"]
}

# ============================================================================
# CLOUD SQL - PostgreSQL 15 + PostGIS
# ============================================================================

resource "google_sql_database_instance" "mantleiq_postgres" {
  name             = var.database_instance_name
  database_version = "POSTGRES_15"
  region           = var.gcp_region
  deletion_protection = false

  settings {
    tier              = var.database_machine_type
    disk_type         = "PD_SSD"
    disk_size         = var.database_disk_size_gb
    disk_autoresize   = true
    disk_autoresize_limit = 500

    # Backup configuration
    backup_configuration {
      enabled                        = true
      start_time                     = "02:00"
      transaction_log_retention_days = 7
      backup_location                = var.gcp_region
    }

    # Connection settings
    ip_configuration {
      require_ssl        = true
      private_network    = google_compute_network.mantleiq_network.id
      enable_private_path_for_cloudsql_mysql_client = true

      # Allow Cloud Run
      authorized_networks {
        name  = "cloudsql-proxy"
        value = "0.0.0.0/0"
      }
    }

    # High availability
    availability_type = "REGIONAL"
    backup_location   = var.gcp_region
  }

  deletion_protection = false

  depends_on = [
    google_compute_network.mantleiq_network,
    google_project_service.required_apis
  ]
}

# PostgreSQL database
resource "google_sql_database" "mantleiq_db" {
  name     = "mantleiq"
  instance = google_sql_database_instance.mantleiq_postgres.name
  charset  = "UTF8"
}

# PostGIS extension
resource "google_sql_database_instance_google_database_flags" "postgis_flags" {
  instance_name = google_sql_database_instance.mantleiq_postgres.name

  flags {
    name  = "shared_preload_libraries"
    value = "pgaudit,pg_stat_statements"
  }
}

# Database user
resource "google_sql_user" "mantleiq_user" {
  name     = var.database_user
  instance = google_sql_database_instance.mantleiq_postgres.name
  password = random_password.db_password.result

  depends_on = [google_sql_database_instance.mantleiq_postgres]
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Create PostGIS extension (via SQL initialization)
resource "google_sql_database_instance_google_database_flags" "postgis_extension" {
  depends_on = [google_sql_database.mantleiq_db]
  instance_name = google_sql_database_instance.mantleiq_postgres.name

  # PostGIS will be installed via SQL script in initialization
}

# ============================================================================
# CLOUD STORAGE
# ============================================================================

resource "google_storage_bucket" "raw_data" {
  name          = "${var.gcp_project_id}-mantleiq-raw"
  location      = var.gcp_region
  force_destroy = true

  versioning {
    enabled = false
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_storage_bucket" "curated_data" {
  name          = "${var.gcp_project_id}-mantleiq-curated"
  location      = var.gcp_region
  force_destroy = true

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_storage_bucket" "reports" {
  name          = "${var.gcp_project_id}-mantleiq-reports"
  location      = var.gcp_region
  force_destroy = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 180
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_storage_bucket" "tiles" {
  name          = "${var.gcp_project_id}-mantleiq-tiles"
  location      = var.gcp_region
  force_destroy = true

  depends_on = [google_project_service.required_apis]
}

# ============================================================================
# ARTIFACT REGISTRY - Docker Images
# ============================================================================

resource "google_artifact_registry_repository" "mantleiq_docker" {
  location      = var.gcp_region
  repository_id = "mantleiq"
  description   = "Docker images for MantleIQ services"
  format        = "DOCKER"

  depends_on = [google_project_service.required_apis]
}

# ============================================================================
# CLOUD RUN - FastAPI Backend
# ============================================================================

resource "google_cloud_run_service" "mantleiq_backend" {
  name     = "mantleiq-backend"
  location = var.gcp_region

  template {
    spec {
      containers {
        image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/mantleiq/mantleiq-backend:latest"

        env {
          name  = "DATABASE_URL"
          value = "postgresql+psycopg2://${var.database_user}:${random_password.db_password.result}@${google_sql_database_instance.mantleiq_postgres.private_ip_address}:5432/mantleiq"
        }

        env {
          name  = "GCS_BUCKET_REPORTS"
          value = google_storage_bucket.reports.name
        }

        env {
          name  = "GCS_BUCKET_CURATED"
          value = google_storage_bucket.curated_data.name
        }

        env {
          name  = "DEBUG"
          value = "false"
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
      }

      service_account_name = google_service_account.cloud_run_sa.email

      # VPC connector for Cloud SQL access
      vpc_access_connector {
        name = google_vpc_access_connector.mantleiq_connector.id
      }

      timeout_seconds = 300
      max_instances   = 100
    }

    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.mantleiq_connector.name
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_artifact_registry_repository.mantleiq_docker,
    google_sql_database_instance.mantleiq_postgres
  ]
}

# Allow public access to backend
resource "google_cloud_run_service_iam_member" "public_backend" {
  service  = google_cloud_run_service.mantleiq_backend.name
  location = google_cloud_run_service.mantleiq_backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Service account for Cloud Run
resource "google_service_account" "cloud_run_sa" {
  account_id   = "mantleiq-cloud-run"
  display_name = "MantleIQ Cloud Run Service Account"
}

# Grant Cloud Run SA access to Cloud SQL
resource "google_project_iam_member" "cloud_run_sql_client" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Grant Cloud Run SA access to Cloud Storage
resource "google_storage_bucket_iam_member" "cloud_run_reports_access" {
  bucket = google_storage_bucket.reports.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_storage_bucket_iam_member" "cloud_run_curated_access" {
  bucket = google_storage_bucket.curated_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# ============================================================================
# VPC ACCESS CONNECTOR
# ============================================================================

resource "google_vpc_access_connector" "mantleiq_connector" {
  name          = "mantleiq-connector"
  region        = var.gcp_region
  ip_cidr_range = "10.1.0.0/28"
  network       = google_compute_network.mantleiq_network.name

  depends_on = [google_compute_network.mantleiq_network]
}

# ============================================================================
# CLOUD SCHEDULER - Daily Pipeline Execution
# ============================================================================

resource "google_cloud_scheduler_job" "daily_pipeline" {
  name             = "mantleiq-daily-pipeline"
  description      = "Daily MantleIQ data pipeline execution"
  schedule         = var.pipeline_schedule  # "0 2 * * *" for 2 AM UTC
  time_zone        = "UTC"
  region           = var.gcp_region
  attempt_deadline = "320s"

  http_target {
    uri        = "${google_cloud_run_service.mantleiq_backend.status[0].url}/run-analysis"
    http_method = "POST"

    headers = {
      "Content-Type" = "application/json"
    }

    body = base64encode(jsonencode({
      basin_id = var.default_basin_id
      mode     = "standard"
    }))

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }

  depends_on = [google_cloud_run_service.mantleiq_backend]
}

# Service account for Cloud Scheduler
resource "google_service_account" "scheduler_sa" {
  account_id   = "mantleiq-scheduler"
  display_name = "MantleIQ Cloud Scheduler Service Account"
}

resource "google_cloud_run_service_iam_member" "scheduler_invoker" {
  service  = google_cloud_run_service.mantleiq_backend.name
  location = google_cloud_run_service.mantleiq_backend.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

# ============================================================================
# CLOUD MONITORING & LOGGING
# ============================================================================

resource "google_monitoring_alert_policy" "backend_error_rate" {
  display_name = "MantleIQ Backend Error Rate"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Cloud Run error rate > 5%"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"mantleiq-backend\" metric.type=\"run.googleapis.com/request_count\" resource.labels.service_name=\"mantleiq-backend\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
    }
  }

  notification_channels = []  # Add notification channels in console
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "backend_url" {
  value       = google_cloud_run_service.mantleiq_backend.status[0].url
  description = "URL of the MantleIQ backend"
}

output "database_connection_string" {
  value       = "postgresql://${var.database_user}:***@${google_sql_database_instance.mantleiq_postgres.private_ip_address}:5432/mantleiq"
  sensitive   = true
  description = "Cloud SQL connection string"
}

output "raw_data_bucket" {
  value       = google_storage_bucket.raw_data.name
  description = "GCS bucket for raw data"
}

output "reports_bucket" {
  value       = google_storage_bucket.reports.name
  description = "GCS bucket for PDF reports"
}

output "artifact_registry_repo" {
  value       = google_artifact_registry_repository.mantleiq_docker.repository_id
  description = "Artifact Registry repository for Docker images"
}
