#!/usr/bin/env python3
"""
Generate test scoring data for a basin.
Creates grid cells and model outputs with random prospectivity scores.
"""

import os
import sys
import uuid
import random
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup paths
sys.path.insert(0, '/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend')
os.environ['DATABASE_URL'] = 'postgresql+psycopg2://postgres:417BajrangNagar%401@db.ttimdqokzalxluwmezcz.supabase.co:5432/postgres'

from app.core.config import settings

# Connect to database
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def generate_grid_cells(basin_id, grid_size=10):
    """Generate grid cells for a basin (10x10 grid)"""
    print(f"Generating {grid_size}x{grid_size} = {grid_size*grid_size} grid cells...")

    cells = []
    for x in range(grid_size):
        for y in range(grid_size):
            cell_id = str(uuid.uuid4())
            # Create simple polygon geometry (bounding box for each cell)
            # Each cell is 1 degree x 1 degree
            lon_min = -100 + x
            lon_max = -100 + x + 1
            lat_min = 35 + y
            lat_max = 35 + y + 1

            geometry = f"POLYGON(({lon_min} {lat_min}, {lon_max} {lat_min}, {lon_max} {lat_max}, {lon_min} {lat_max}, {lon_min} {lat_min}))"
            centroid = f"POINT({lon_min + 0.5} {lat_min + 0.5})"

            sql = text("""
                INSERT INTO grid_cells (id, basin_id, grid_x, grid_y, geometry, centroid, lat, lon, area_km2, data_completeness)
                VALUES (:id, :basin_id, :x, :y, ST_GeomFromText(:geom, 4326), ST_GeomFromText(:centroid, 4326), :lat, :lon, 100.0, 0.8)
                ON CONFLICT (id) DO NOTHING
            """)

            db.execute(sql, {
                "id": cell_id,
                "basin_id": basin_id,
                "x": x,
                "y": y,
                "geom": geometry,
                "centroid": centroid,
                "lat": lat_min + 0.5,
                "lon": lon_min + 0.5
            })

            cells.append((cell_id, x, y))

    db.commit()
    print(f"✓ Created {len(cells)} grid cells")
    return cells

def generate_model_outputs(basin_id, cells):
    """Generate model outputs with random scores for each cell"""
    print(f"Generating model outputs with scores...")

    for idx, (cell_id, grid_x, grid_y) in enumerate(cells):
        # Generate realistic scores
        # Create hotspots with higher scores
        center_x, center_y = 5, 5
        dist = ((grid_x - center_x)**2 + (grid_y - center_y)**2)**0.5
        base_score = max(0.3, 0.9 - (dist / 10))

        # Add some randomness
        prospectivity_score = max(0.1, min(0.99, base_score + random.gauss(0, 0.1)))

        # Component scores (should sum roughly to 1.0, weighted by importance)
        f_generation = prospectivity_score * 0.30 + random.gauss(0, 0.05)
        f_fluid_interaction = prospectivity_score * 0.20 + random.gauss(0, 0.05)
        f_structural_pathways = prospectivity_score * 0.20 + random.gauss(0, 0.05)
        f_trap_retention = prospectivity_score * 0.15 + random.gauss(0, 0.05)
        f_surface_indicators = prospectivity_score * 0.10 + random.gauss(0, 0.05)
        f_thermodynamic = prospectivity_score * 0.05 + random.gauss(0, 0.05)

        # Clamp to valid ranges
        f_generation = max(0, min(1, f_generation))
        f_fluid_interaction = max(0, min(1, f_fluid_interaction))
        f_structural_pathways = max(0, min(1, f_structural_pathways))
        f_trap_retention = max(0, min(1, f_trap_retention))
        f_surface_indicators = max(0, min(1, f_surface_indicators))
        f_thermodynamic = max(0, min(1, f_thermodynamic))

        confidence_score = 0.5 + random.uniform(0, 0.5)

        # Determine score class
        if prospectivity_score >= 0.8:
            score_class = "high_priority"
        elif prospectivity_score >= 0.65:
            score_class = "strong_prospect"
        elif prospectivity_score >= 0.5:
            score_class = "moderate"
        elif prospectivity_score >= 0.35:
            score_class = "weak"
        else:
            score_class = "low"

        sql = text("""
            INSERT INTO model_outputs (
                id, grid_cell_id, basin_id, model_version,
                f_generation, f_fluid_interaction, f_structural_pathways,
                f_trap_retention, f_surface_indicators, f_thermodynamic,
                rule_score, ml_score, ensemble_score,
                confidence_score, final_score, rank_global, rank_basin, score_class
            )
            VALUES (
                :id, :grid_cell_id, :basin_id, :model_version,
                :f_gen, :f_fluid, :f_struct, :f_trap, :f_surface, :f_thermo,
                :rule, :ml, :ensemble, :confidence, :final, 0, 0, :score_class
            )
            ON CONFLICT (id) DO NOTHING
        """)

        db.execute(sql, {
            "id": str(uuid.uuid4()),
            "grid_cell_id": cell_id,
            "basin_id": basin_id,
            "model_version": "prospectivity_v1",
            "f_gen": f_generation,
            "f_fluid": f_fluid_interaction,
            "f_struct": f_structural_pathways,
            "f_trap": f_trap_retention,
            "f_surface": f_surface_indicators,
            "f_thermo": f_thermodynamic,
            "rule": prospectivity_score,
            "ml": prospectivity_score + random.gauss(0, 0.05),
            "ensemble": prospectivity_score,
            "confidence": confidence_score,
            "final": prospectivity_score,
            "score_class": score_class
        })

        if (idx + 1) % 25 == 0:
            print(f"  Created {idx + 1}/{len(cells)} model outputs...")

    db.commit()
    print(f"✓ Created model outputs for {len(cells)} cells")

def main():
    basin_id = "11e757b7-ddde-48dc-8c7a-619cfa350930"  # Kansas Rift Basin - Supabase Test

    print(f"Generating test data for basin: {basin_id}")
    print("=" * 60)

    try:
        # Generate grid cells
        cells = generate_grid_cells(basin_id, grid_size=10)

        # Generate model outputs
        generate_model_outputs(basin_id, cells)

        print("=" * 60)
        print("✓ Test data generation complete!")
        print(f"Created {len(cells)} cells with prospectivity scores")
        print(f"Visit http://localhost:5173 and select 'Kansas Rift Basin - Supabase Test'")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
