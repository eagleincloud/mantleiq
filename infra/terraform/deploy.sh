#!/bin/bash

################################################################################
# MantleIQ GCP Deployment Script
#
# Automated deployment of MantleIQ to Google Cloud Platform
# Usage: ./deploy.sh [plan|apply|destroy|logs]
#
# Examples:
#   ./deploy.sh plan              # Generate deployment plan
#   ./deploy.sh apply             # Deploy to GCP
#   ./deploy.sh destroy           # Remove all resources
#   ./deploy.sh logs              # View deployment logs
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
TFVARS_FILE="$SCRIPT_DIR/terraform.tfvars"
TFPLAN_FILE="$SCRIPT_DIR/tfplan"
LOG_FILE="$SCRIPT_DIR/deploy.log"

# Helper functions
log() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        error "Terraform is not installed. Visit https://www.terraform.io/downloads.html"
    fi
    success "Terraform found: $(terraform version | head -1)"

    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI is not installed. Visit https://cloud.google.com/sdk/docs/install"
    fi
    success "gcloud found: $(gcloud --version | head -1)"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Visit https://docs.docker.com/get-docker/"
    fi
    success "Docker found: $(docker --version)"

    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        error "Not authenticated with gcloud. Run: gcloud auth login"
    fi
    success "gcloud authentication verified"
}

# Validate Terraform configuration
validate_terraform() {
    log "Validating Terraform configuration..."
    cd "$SCRIPT_DIR"

    # Check tfvars file exists
    if [ ! -f "$TFVARS_FILE" ]; then
        error "terraform.tfvars not found. Copy terraform.tfvars.example to terraform.tfvars and update values."
    fi

    # Initialize Terraform
    terraform init -upgrade

    # Validate syntax
    terraform validate

    success "Terraform configuration is valid"
}

# Generate deployment plan
plan_deployment() {
    log "Generating deployment plan..."
    cd "$SCRIPT_DIR"

    terraform plan -out="$TFPLAN_FILE" -var-file="$TFVARS_FILE"

    log "Plan saved to: $TFPLAN_FILE"
    log "Review the plan above carefully before applying."
    success "Plan generation complete"
}

# Apply deployment
apply_deployment() {
    log "Applying Terraform configuration..."
    cd "$SCRIPT_DIR"

    if [ ! -f "$TFPLAN_FILE" ]; then
        warning "No plan file found. Generating plan first..."
        plan_deployment
    fi

    read -p "Continue with deployment? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        warning "Deployment cancelled"
        exit 0
    fi

    terraform apply "$TFPLAN_FILE"

    success "Deployment completed successfully"

    # Save outputs
    log "Saving deployment outputs..."
    terraform output -json > "$SCRIPT_DIR/outputs.json"
    success "Outputs saved to: $SCRIPT_DIR/outputs.json"
}

# Deploy Docker image to Cloud Run
deploy_image() {
    log "Building and deploying Docker image..."
    cd "$PROJECT_DIR"

    # Get project ID from terraform outputs
    PROJECT_ID=$(terraform -chdir="$SCRIPT_DIR" output -raw gcp_project_id 2>/dev/null)
    REGION=$(grep "gcp_region" "$TFVARS_FILE" | cut -d'"' -f2)

    if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; then
        error "Could not determine PROJECT_ID or REGION from terraform outputs"
    fi

    IMAGE_FULL="${REGION}-docker.pkg.dev/${PROJECT_ID}/mantleiq/mantleiq-backend:latest"

    log "Building Docker image: $IMAGE_FULL"
    docker build -f backend/Dockerfile -t "$IMAGE_FULL" .

    log "Configuring Docker authentication..."
    gcloud auth configure-docker "${REGION}-docker.pkg.dev"

    log "Pushing image to Artifact Registry..."
    docker push "$IMAGE_FULL"

    success "Docker image deployed"
}

# View deployment logs
view_logs() {
    log "Recent deployment logs:"
    tail -50 "$LOG_FILE"
}

# Initialize database
init_database() {
    log "Initializing database schema..."
    cd "$SCRIPT_DIR"

    # Get database connection info from outputs
    DB_INSTANCE=$(terraform output -raw database_instance_name 2>/dev/null)
    REGION=$(grep "gcp_region" "$TFVARS_FILE" | cut -d'"' -f2)
    PROJECT_ID=$(terraform output -raw gcp_project_id 2>/dev/null)

    if [ -z "$DB_INSTANCE" ] || [ -z "$REGION" ] || [ -z "$PROJECT_ID" ]; then
        error "Could not get database connection info from outputs"
    fi

    log "Starting Cloud SQL Proxy for $DB_INSTANCE..."
    log "Note: You may need to configure Cloud SQL Auth proxy authentication"
    log "Run in another terminal: cloud_sql_proxy -instances=${PROJECT_ID}:${REGION}:${DB_INSTANCE}=tcp:5432"
    log "Then run schema import: psql -h localhost -U mantleiq_user -d mantleiq < infra/sql/001_schema.sql"
}

# Destroy resources
destroy_resources() {
    log "Preparing to destroy all GCP resources..."
    cd "$SCRIPT_DIR"

    read -p "This will DELETE all resources. Type 'destroy' to confirm: " -r
    if [[ $REPLY != "destroy" ]]; then
        warning "Destruction cancelled"
        exit 0
    fi

    terraform destroy -var-file="$TFVARS_FILE"

    success "Resources destroyed"
}

# Test deployment
test_deployment() {
    log "Testing deployment..."
    cd "$SCRIPT_DIR"

    BACKEND_URL=$(terraform output -raw backend_url 2>/dev/null)

    if [ -z "$BACKEND_URL" ]; then
        error "Could not get backend URL from outputs"
    fi

    log "Testing Cloud Run endpoint: $BACKEND_URL"

    # Try to reach the backend
    if curl -s "${BACKEND_URL}/health" > /dev/null 2>&1; then
        success "Backend is healthy"
    else
        warning "Backend not responding (may be in cold start)"
        log "URL: $BACKEND_URL/health"
    fi
}

# Show summary
show_summary() {
    log "Deployment Summary:"
    echo "==================="

    if [ -f "$SCRIPT_DIR/outputs.json" ]; then
        echo ""
        echo "Outputs:"
        jq '.' "$SCRIPT_DIR/outputs.json" 2>/dev/null || echo "See outputs.json for details"
    fi

    echo ""
    echo "Next steps:"
    echo "1. Build and push Docker image: ./deploy.sh build-image"
    echo "2. Initialize database: ./deploy.sh init-db"
    echo "3. View logs: ./deploy.sh logs"
    echo "4. Test deployment: ./deploy.sh test"
    echo ""
}

# Main command dispatcher
main() {
    local command="${1:-help}"

    case "$command" in
        plan)
            check_prerequisites
            validate_terraform
            plan_deployment
            ;;
        apply)
            check_prerequisites
            validate_terraform
            apply_deployment
            show_summary
            ;;
        deploy-image)
            deploy_image
            success "Image deployed to Cloud Run"
            ;;
        init-db)
            init_database
            ;;
        test)
            test_deployment
            ;;
        logs)
            view_logs
            ;;
        destroy)
            check_prerequisites
            destroy_resources
            ;;
        status)
            cd "$SCRIPT_DIR"
            log "Current Terraform state:"
            terraform state list | head -20
            ;;
        help|*)
            cat << EOF
MantleIQ GCP Deployment Script

Usage: ./deploy.sh [COMMAND]

Commands:
  plan            Generate deployment plan (review before applying)
  apply           Deploy infrastructure to GCP (requires plan)
  deploy-image    Build and push Docker image to Artifact Registry
  init-db         Instructions for database initialization
  test            Test cloud run endpoint health
  logs            View deployment logs
  destroy         Remove all GCP resources (CAREFUL!)
  status          Show current Terraform state
  help            Show this help message

Examples:
  # First time deployment
  ./deploy.sh plan
  ./deploy.sh apply
  ./deploy.sh deploy-image
  ./deploy.sh init-db
  ./deploy.sh test

  # Tear everything down
  ./deploy.sh destroy

Configuration:
  Edit terraform.tfvars before running deploy

Documentation:
  See ../../GCP_DEPLOYMENT_GUIDE.md for complete guide

EOF
            ;;
    esac
}

# Run main function
main "$@"
