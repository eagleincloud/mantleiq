#!/bin/bash

# MantleIQ Data Pipeline - Quick Start
# Run: bash /Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/data/QUICK_START.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DATA_DIR="$SCRIPT_DIR"
RAW_DIR="$DATA_DIR/raw"
CURATED_DIR="$DATA_DIR/curated"
REPORTS_DIR="$DATA_DIR/reports"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}MantleIQ Data Pipeline - Quick Start${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "${YELLOW}$1${NC}"
    echo "----------------------------------------"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print info
print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check prerequisites
print_section "1. CHECKING PREREQUISITES"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.8+${NC}"
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

# Check if pip packages are available
python3 -c "import geopandas, rasterio, requests, pandas" 2>/dev/null && \
    print_success "Required packages found" || {
    echo -e "${YELLOW}⚠ Installing required packages...${NC}"
    pip install -q geopandas rasterio requests pandas sqlalchemy psycopg2-binary
    print_success "Packages installed"
}

# Check database connectivity
print_section "2. CHECKING DATABASE CONNECTION"
python3 << 'EOF'
import sys
import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg2://postgres:417BajrangNagar%401@db.ttimdqokzalxluwmezcz.supabase.co:5432/postgres'

try:
    from sqlalchemy import create_engine, text
    from app.core.config import settings

    engine = create_engine(settings.database_url, echo=False)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"\033[0;32m✓ Connected to PostgreSQL\033[0m")
        print(f"  {version[:60]}...")
except Exception as e:
    print(f"\033[0;31m✗ Database connection failed: {e}\033[0m")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Database connection check failed${NC}"
    exit 1
fi

# Show folder structure
print_section "3. DATA PIPELINE STRUCTURE"
print_info "Raw data folder:     $RAW_DIR"
print_info "Curated data folder: $CURATED_DIR"
print_info "Reports folder:      $REPORTS_DIR"
echo ""
ls -la "$DATA_DIR" | grep '^d' | awk '{print "  📁 " $NF}'

# Show configuration
print_section "4. BASIN CONFIGURATION"
print_info "Test Basin: Kansas Rift"
print_info "Basin ID: 11e757b7-ddde-48dc-8c7a-619cfa350930"
print_info "Region: -98°W to -93°W, 37°N to 40°N"
print_info "Grid: 10×10 cells (100 total)"

# Menu
print_section "5. ACTIONS"
echo ""
echo "1) View data pipeline documentation"
echo "2) Run full pipeline (download → normalize → load)"
echo "3) Download data only"
echo "4) Normalize existing raw data"
echo "5) Validate curated data"
echo "6) View pipeline reports"
echo "7) Exit"
echo ""

read -p "Select action (1-7): " choice

case $choice in
    1)
        print_section "Data Pipeline Documentation"
        cat "$DATA_DIR/DATA_PIPELINE_README.md"
        ;;
    2)
        print_section "Running Full Pipeline"
        python3 << 'EOPYTHON'
import sys
sys.path.insert(0, '/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend')
from scripts.data_pipeline import DataPipeline

pipeline = DataPipeline()
kansas_bounds = (-98.0, 37.0, -93.0, 40.0)
kansas_basin_id = "11e757b7-ddde-48dc-8c7a-619cfa350930"
pipeline.run_pipeline(kansas_bounds, kansas_basin_id)
EOPYTHON
        ;;
    3)
        print_section "Download Phase"
        python3 << 'EOPYTHON'
import sys
sys.path.insert(0, '/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend')
from scripts.data_pipeline import DataPipeline

pipeline = DataPipeline()
kansas_bounds = (-98.0, 37.0, -93.0, 40.0)

pipeline.download_faults(kansas_bounds)
pipeline.download_gravity(kansas_bounds)
pipeline.download_magnetic(kansas_bounds)
pipeline.download_geology(kansas_bounds)
pipeline.download_heatflow(kansas_bounds)

print("\n✓ Download phase complete!")
print(f"Check {RAW_DIR} for downloaded files")
EOPYTHON
        ;;
    4)
        print_section "Normalize Phase"
        echo "Finding raw files to normalize..."
        find "$RAW_DIR" -type f \( -name "*.geojson" -o -name "*.shp" -o -name "*.tif" -o -name "*.csv" \) -exec echo "  Found: {}" \;
        echo ""
        echo "Run: python3 scripts/data_pipeline.py to normalize files"
        ;;
    5)
        print_section "Validate Phase"
        python3 << 'EOPYTHON'
import sys
from pathlib import Path
sys.path.insert(0, '/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend')
from scripts.data_pipeline import DataPipeline

pipeline = DataPipeline()
curated_dir = Path('/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/data/curated')

if curated_dir.exists():
    for file in curated_dir.rglob('*'):
        if file.is_file() and not file.name.startswith('.'):
            pipeline.validate_data(file)
else:
    print("No curated files found. Run normalization first.")
EOPYTHON
        ;;
    6)
        print_section "Pipeline Reports"
        if [ -d "$REPORTS_DIR" ] && [ "$(ls -A $REPORTS_DIR)" ]; then
            ls -lht "$REPORTS_DIR" | tail -5
            echo ""
            echo "Latest report:"
            cat "$REPORTS_DIR"/*.json 2>/dev/null | head -c 500
        else
            echo "No reports found. Run the pipeline first."
        fi
        ;;
    7)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid selection${NC}"
        exit 1
        ;;
esac

echo ""
print_success "Action completed!"
echo ""
echo "For more information, see: $DATA_DIR/DATA_PIPELINE_README.md"
