variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.gcp_project_id))
    error_message = "Project ID must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "gcp_region" {
  description = "GCP Region for deployment"
  type        = string
  default     = "us-central1"
  validation {
    condition     = contains(["us-central1", "us-east1", "us-west1", "europe-west1", "asia-southeast1"], var.gcp_region)
    error_message = "Region must be a valid GCP region."
  }
}

variable "database_instance_name" {
  description = "Cloud SQL instance name"
  type        = string
  default     = "mantleiq-postgres"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*[a-z0-9]$", var.database_instance_name))
    error_message = "Instance name must start with a letter, contain only lowercase letters/numbers/hyphens, and end with alphanumeric."
  }
}

variable "database_machine_type" {
  description = "Cloud SQL machine type"
  type        = string
  default     = "db-custom-4-16"
  validation {
    condition     = can(regex("^db-", var.database_machine_type))
    error_message = "Machine type must start with 'db-'."
  }
}

variable "database_disk_size_gb" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 100
  validation {
    condition     = var.database_disk_size_gb >= 10 && var.database_disk_size_gb <= 65536
    error_message = "Disk size must be between 10 and 65536 GB."
  }
}

variable "database_user" {
  description = "Cloud SQL database username"
  type        = string
  default     = "mantleiq"
  sensitive   = false
  validation {
    condition     = can(regex("^[a-z_][a-z0-9_]*$", var.database_user))
    error_message = "Username must start with a letter or underscore and contain only lowercase letters, numbers, and underscores."
  }
}

variable "default_basin_id" {
  description = "Default basin ID for pipeline scheduling"
  type        = string
  default     = "kansas-rift-demo"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.default_basin_id))
    error_message = "Basin ID must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "pipeline_schedule" {
  description = "Cloud Scheduler cron expression for daily pipeline"
  type        = string
  default     = "0 2 * * *"  # 2 AM UTC daily
  validation {
    condition     = can(regex("^(((\\*|\\d{1,2})(,(\\d{1,2}))*|-\\d{1,2}|/\\d{1,2})?\\s*){5}$", var.pipeline_schedule))
    error_message = "Must be a valid cron expression (5 fields: minute hour day-of-month month day-of-week)."
  }
}

variable "enable_private_ip" {
  description = "Enable private IP for Cloud SQL"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_location" {
  description = "Location for backup storage"
  type        = string
  default     = "us"
  validation {
    condition     = contains(["us", "eu", "asia"], var.backup_location)
    error_message = "Backup location must be us, eu, or asia."
  }
}

variable "enable_monitoring" {
  description = "Enable Cloud Monitoring and logging"
  type        = bool
  default     = true
}

variable "cloud_run_memory" {
  description = "Cloud Run memory allocation"
  type        = string
  default     = "2Gi"
  validation {
    condition     = contains(["256Mi", "512Mi", "1Gi", "2Gi", "4Gi", "6Gi", "8Gi"], var.cloud_run_memory)
    error_message = "Memory must be one of: 256Mi, 512Mi, 1Gi, 2Gi, 4Gi, 6Gi, 8Gi."
  }
}

variable "cloud_run_cpu" {
  description = "Cloud Run CPU allocation"
  type        = string
  default     = "2"
  validation {
    condition     = contains(["0.25", "0.5", "1", "2", "4", "6", "8"], var.cloud_run_cpu)
    error_message = "CPU must be one of: 0.25, 0.5, 1, 2, 4, 6, 8."
  }
}

variable "cloud_run_max_instances" {
  description = "Cloud Run maximum instances"
  type        = number
  default     = 100
  validation {
    condition     = var.cloud_run_max_instances >= 1 && var.cloud_run_max_instances <= 1000
    error_message = "Max instances must be between 1 and 1000."
  }
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    application = "mantleiq"
    environment = "production"
    team        = "geospatial-ai"
    managed_by  = "terraform"
  }
}
