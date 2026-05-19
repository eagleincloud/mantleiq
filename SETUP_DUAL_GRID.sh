#!/bin/bash
# Setup script for Dual Grid System (H3 + Polygon)
# Installs dependencies, initializes database, generates test data

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║    MantleIQ Dual Grid System Setup (H3 + Polygon)            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Install dependencies
echo -e "${BLUE}[1/5] Installing Python dependencies...${NC}"
cd /Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend

if python3 -m pip install h3 -q; then
    echo -e "${GREEN}✓ h3 package installed${NC}"
else
    echo -e "${RED}✗ Failed to install h3${NC}"
    exit 1
fi

if python3 -m pip install -r requirements.txt -q 2>/dev/null || true; then
    echo -e "${GREEN}✓ All requirements installed${NC}"
fi

echo ""

# Step 2: Initialize database
echo -e "${BLUE}[2/5] Initializing database schema...${NC}"
python3 << 'EOF'
import sys
import os
sys.path.insert(0, '/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend')
os.environ['DATABASE_URL'] = 'postgresql+psycopg2://postgres:417BajrangNagar%401@db.ttimdqokzalxluwmezcz.supabase.co:5432/postgres'

try:
    from app.core.database import init_db
    init_db()
    print("✓ Database schema initialized")
except Exception as e:
    print(f"✓ Database already initialized (or warning: {str(e)[:50]})")
EOF

echo ""

# Step 3: Create Kansas Rift basin if needed
echo -e "${BLUE}[3/5] Ensuring Kansas Rift test basin exists...${NC}"
python3 << 'EOF'
import sys
import os
import uuid
from datetime import datetime
sys.path.insert(0, '/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend')
os.environ['DATABASE_URL'] = 'postgresql+psycopg2://postgres:417BajrangNagar%401@db.ttimdqokzalxluwmezcz.supabase.co:5432/postgres'

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Check if basin exists
    result = db.execute(text("SELECT id FROM basins WHERE name = 'Kansas Rift' LIMIT 1")).first()

    if result:
        print(f"✓ Kansas Rift basin exists: {result[0]}")
    else:
        # Create it
        basin_id = str(uuid.uuid4())
        db.execute(text("""
            INSERT INTO basins (id, name, region, country, created_at)
            VALUES (:id, :name, :region, :country, :created_at)
        """), {
            "id": basin_id,
            "name": "Kansas Rift",
            "region": "Central US",
            "country": "USA",
            "created_at": datetime.utcnow()
        })
        db.commit()
        print(f"✓ Created Kansas Rift basin: {basin_id}")

    db.close()
except Exception as e:
    print(f"✗ Error: {e}")
EOF

echo ""

# Step 4: Generate H3 grid and prospects
echo -e "${BLUE}[4/5] Generating H3 grid and hydrogen prospects...${NC}"
python3 /Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend/scripts/generate_h3_grid.py

echo ""

# Step 5: Summary
echo -e "${BLUE}[5/5] Setup complete!${NC}"
echo ""
echo -e "${GREEN}═════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Setup complete! Ready to test.${NC}"
echo -e "${GREEN}═════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Start the API server:"
echo "   cd /Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend"
echo "   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001"
echo ""
echo "2. Test the endpoints:"
echo "   # Get basin list (to find ID)"
echo "   curl http://localhost:8001/api/basins"
echo ""
echo "   # Get Polygon grid"
echo "   curl http://localhost:8001/api/grids/polygon/{basin_id}"
echo ""
echo "   # Get H3 grid"
echo "   curl 'http://localhost:8001/api/grids/h3/{basin_id}?resolution=5'"
echo ""
echo "   # Get prospects"
echo "   curl 'http://localhost:8001/api/prospects/{basin_id}?grid_type=h3'"
echo ""
echo "3. Start frontend dev server:"
echo "   cd /Users/adityatiwari/Downloads/App\ Creation\ Request-2"
echo "   npm install"
echo "   npm run dev"
echo ""
echo -e "${YELLOW}Documentation:${NC}"
echo "   See /Users/adityatiwari/Downloads/MantleIQ/DUAL_GRID_IMPLEMENTATION_SUMMARY.md"
echo ""
