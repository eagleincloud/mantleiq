#!/bin/bash
set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}MANTLEIQ LOCAL PIPELINE RUNNER${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

PROJECT_DIR="/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp"
STORAGE_DIR="$PROJECT_DIR/local_storage"
LOGS_DIR="$STORAGE_DIR/logs"
OUTPUT_DIR="$STORAGE_DIR/outputs"
REPORTS_DIR="$STORAGE_DIR/reports"

# Ensure directories exist
mkdir -p "$LOGS_DIR" "$OUTPUT_DIR" "$REPORTS_DIR"

echo -e "${BLUE}📁 Storage Configuration:${NC}"
echo "   Storage Root: $STORAGE_DIR"
echo "   Databases:   $STORAGE_DIR/databases"
echo "   Reports:     $REPORTS_DIR"
echo "   Logs:        $LOGS_DIR"
echo "   Outputs:     $OUTPUT_DIR"
echo ""

# Check if Prefect is installed
echo -e "${BLUE}🔍 Checking dependencies...${NC}"
if ! python -c "import prefect" 2>/dev/null; then
    echo -e "${YELLOW}Installing Prefect and dependencies...${NC}"
    cd "$PROJECT_DIR/backend"
    pip install -q -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ Prefect already installed${NC}"
fi
echo ""

# Check Docker services
echo -e "${BLUE}🐳 Checking Docker services...${NC}"
docker_status=$(docker-compose ps 2>/dev/null | grep -c "running" || echo "0")
if [ "$docker_status" -gt 0 ]; then
    echo -e "${GREEN}✅ Docker services running${NC}"
    docker-compose ps
else
    echo -e "${YELLOW}⏳ Waiting for Docker services to start...${NC}"
fi
echo ""

# Run the Prefect pipeline
echo -e "${BLUE}🚀 Launching Prefect Pipeline...${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

cd "$PROJECT_DIR"

# Run with detailed logging
BASIN_NAME="Kansas Rift Basin - $(date +'%Y-%m-%d %H:%M:%S')"

python -u backend/workflows/local_manual_pipeline.py "$BASIN_NAME" 2>&1 | tee "$LOGS_DIR/pipeline_$(date +'%Y%m%d_%H%M%S').log"

echo ""
echo -e "${BLUE}================================================================================${NC}"
echo -e "${GREEN}✅ PIPELINE EXECUTION COMPLETE${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

# List generated artifacts
echo -e "${YELLOW}📊 Generated Artifacts:${NC}"
echo ""

echo -e "${YELLOW}Database Files:${NC}"
ls -lh "$STORAGE_DIR/databases/" 2>/dev/null || echo "   No database files yet"
echo ""

echo -e "${YELLOW}Reports:${NC}"
ls -lh "$REPORTS_DIR/" 2>/dev/null || echo "   No reports yet"
echo ""

echo -e "${YELLOW}Logs:${NC}"
ls -lh "$LOGS_DIR/" 2>/dev/null | tail -3 || echo "   No logs yet"
echo ""

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Local storage location: ${GREEN}$STORAGE_DIR${BLUE}${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""
