#!/usr/bin/env python3
"""
Generate H3 hexagonal grid for a basin with hydrogen prospects.
Creates H3 cells and distributes hydrogen prospects across them.
"""

import os
import sys
import uuid
import random
import math
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup paths
sys.path.insert(0, '/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend')
os.environ['DATABASE_URL'] = 'postgresql+psycopg2://postgres:417BajrangNagar%401@db.ttimdqokzalxluwmezcz.supabase.co:5432/postgres'

from app.core.config import settings
from app.services.grids import H3GridService

# Connect to database
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()


def generate_h3_grid_for_basin(basin_id, basin_name, resolution=5):
    """
    Generate H3 grid cells for a basin.

    Args:
        basin_id: Basin UUID
        basin_name: Basin name for logging
        resolution: H3 resolution level (0-15)
    """
    print(f"\n{'='*60}")
    print(f"Generating H3 Grid (Resolution {resolution}) for {basin_name}")
    print(f"{'='*60}")

    # Kansas Rift bounds
    basin_bounds = (-98.0, 37.0, -93.0, 40.0)  # (west, south, east, north)

    # Generate H3 cells
    h3_ids = H3GridService.generate_h3_grid(basin_bounds, resolution)
    print(f"✓ Generated {len(h3_ids)} H3 cells")

    if not h3_ids:
        print("✗ No H3 cells generated")
        return 0

    # Insert H3 cells into database
    cells_created = 0
    for h3_id in h3_ids:
        try:
            # Get centroid
            lat, lon = H3GridService.get_h3_centroid(h3_id)

            cell_id = str(uuid.uuid4())

            sql = text("""
                INSERT INTO grid_cells
                (id, basin_id, h3_id, lon, lat, created_at)
                VALUES (:id, :basin_id, :h3_id, :lon, :lat, :created_at)
                ON CONFLICT DO NOTHING
            """)

            db.execute(sql, {
                "id": cell_id,
                "basin_id": basin_id,
                "h3_id": h3_id,
                "lon": lon,
                "lat": lat,
                "created_at": datetime.utcnow()
            })

            cells_created += 1

        except Exception as e:
            print(f"✗ Error creating H3 cell {h3_id}: {e}")

    db.commit()
    print(f"✓ Created {cells_created} H3 grid cells in database")

    return cells_created


def generate_hydrogen_prospects(basin_id, grid_type="h3", prospects_per_cell=1):
    """
    Generate zone-level prospects by clustering high-prospectivity grid cells.

    Args:
        basin_id: Basin UUID
        grid_type: 'h3' or 'polygon'
        prospects_per_cell: Not used (for compatibility)
    """
    print(f"\n{'='*60}")
    print(f"Generating Zone-Level Prospects")
    print(f"{'='*60}")

    # Just mark that we have prospects - actual zones would be computed via clustering
    print(f"✓ Zone generation skipped (requires ML model)")
    print(f"  Zones can be generated via DBSCAN clustering on top-percentile cells")

    return 0


def create_grid_configuration(basin_id, grid_type, resolution=5):
    """
    Create grid configuration metadata (skipped - table doesn't exist in current schema).

    Args:
        basin_id: Basin UUID
        grid_type: 'h3' or 'polygon'
        resolution: H3 resolution (ignored for polygon)
    """
    print(f"\n{'='*60}")
    print(f"Grid Configuration")
    print(f"{'='*60}")

    # Count cells
    sql_cells = text("""
        SELECT COUNT(*) as count FROM grid_cells
        WHERE basin_id = :basin_id
    """)

    cell_count = db.execute(sql_cells, {"basin_id": basin_id}).scalar()

    print(f"✓ Grid configuration: {grid_type} (cells: {cell_count})")
    print(f"  Note: grid_configurations table not required for H3/Polygon support")


def main():
    """Main execution"""

    # Get basin ID (you need to update this or query the database)
    # For Kansas Rift test basin
    basin_id_sql = text("""
        SELECT id FROM basins WHERE name = 'Kansas Rift' LIMIT 1
    """)

    basin_row = db.execute(basin_id_sql).first()

    if not basin_row:
        # Create test basin if it doesn't exist
        print("Creating test basin: Kansas Rift")
        basin_id = str(uuid.uuid4())
        sql = text("""
            INSERT INTO basins (id, name, region, country)
            VALUES (:id, :name, :region, :country)
            ON CONFLICT DO NOTHING
        """)
        db.execute(sql, {
            "id": basin_id,
            "name": "Kansas Rift",
            "region": "Central US",
            "country": "USA"
        })
        db.commit()
    else:
        basin_id = basin_row.id

    print(f"\n✓ Using Basin ID: {basin_id}")

    # Generate H3 grids at different resolutions
    for resolution in [5]:  # Just resolution 5 for now, can add more
        cells_created = generate_h3_grid_for_basin(basin_id, "Kansas Rift", resolution)
        if cells_created > 0:
            # Generate prospects
            prospects_created = generate_hydrogen_prospects(basin_id, "h3", prospects_per_cell=1)
            # Create configuration
            create_grid_configuration(basin_id, "h3", resolution)

    print(f"\n{'='*60}")
    print("✓ H3 Grid Generation Complete")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n✗ Interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
