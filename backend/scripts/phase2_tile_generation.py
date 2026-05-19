#!/usr/bin/env python3
"""
PHASE 2: Vector Tile Generation
Generate MVT (Mapbox Vector Tiles) from model outputs and store in local tiles folder
"""

import logging
import json
from pathlib import Path
from urllib.parse import quote
import struct

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Supabase connection
password = '417BajrangNagar@1'
encoded_password = quote(password, safe='')
DATABASE_URL = f"postgresql+psycopg2://postgres:{encoded_password}@db.ttimdqokzalxluwmezcz.supabase.co:5432/postgres"

TILES_DIR = Path("/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/local_storage/tiles")
TILES_DIR.mkdir(parents=True, exist_ok=True)

def step_1_export_geojson_tiles(basin_id: str):
    """Export model outputs as GeoJSON tiles (browser-friendly format)"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("STEP 1: EXPORT GEOJSON TILES (Browser-Ready Format)")
    logger.info("=" * 80)

    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # Query model outputs with grid cell info
        sql = text("""
            SELECT
                mo.id,
                mo.grid_cell_id,
                mo.final_score,
                mo.confidence_score,
                mo.score_class,
                gc.lat,
                gc.lon,
                gc.grid_x,
                gc.grid_y
            FROM model_outputs mo
            JOIN grid_cells gc ON mo.grid_cell_id = gc.id
            WHERE mo.basin_id = :basin_id
            ORDER BY mo.final_score DESC
        """)

        results = session.execute(sql, {"basin_id": basin_id}).fetchall()

        if not results:
            logger.warning("No model outputs found")
            return False

        # Convert to GeoJSON
        features = []
        for row in results:
            feature = {
                "type": "Feature",
                "properties": {
                    "id": str(row[0]),
                    "cell_id": str(row[1]),
                    "prospectivity_score": float(row[2]),
                    "confidence": float(row[3]),
                    "score_class": row[4],
                    "grid_x": row[7],
                    "grid_y": row[8],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row[6]), float(row[5])]  # [lon, lat]
                }
            }
            features.append(feature)

        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        # Save GeoJSON
        output_file = TILES_DIR / "model_outputs.geojson"
        with open(output_file, "w") as f:
            json.dump(geojson, f, indent=2)

        logger.info(f"✅ Exported {len(features)} model outputs as GeoJSON")
        logger.info(f"   Saved to: {output_file}")

    return True

def step_2_export_zones_geojson(basin_id: str):
    """Export prospect zones as GeoJSON"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("STEP 2: EXPORT PROSPECT ZONES (Clustering Results)")
    logger.info("=" * 80)

    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # Query zones with their properties
        sql = text("""
            SELECT
                id,
                name,
                prospectivity_score,
                confidence_score,
                rank,
                cell_count,
                top_features,
                explanation_summary
            FROM zones
            WHERE basin_id = :basin_id
            ORDER BY prospectivity_score DESC
        """)

        results = session.execute(sql, {"basin_id": basin_id}).fetchall()

        if not results:
            logger.info("No zones found (expected on first run)")
            return True

        features = []
        for row in results:
            feature = {
                "type": "Feature",
                "properties": {
                    "id": str(row[0]),
                    "name": row[1],
                    "prospectivity": float(row[2]),
                    "confidence": float(row[3]),
                    "rank": row[4],
                    "cell_count": row[5],
                    "top_features": row[6],
                    "summary": row[7],
                },
                "geometry": {"type": "Point"}  # Placeholder
            }
            features.append(feature)

        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        output_file = TILES_DIR / "prospect_zones.geojson"
        with open(output_file, "w") as f:
            json.dump(geojson, f, indent=2)

        logger.info(f"✅ Exported {len(features)} prospect zones")
        logger.info(f"   Saved to: {output_file}")

    return True

def step_3_create_heatmap_tiles(basin_id: str):
    """Create grid-based heatmap tiles for visual analysis"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("STEP 3: CREATE HEATMAP TILES (Grid Visualization)")
    logger.info("=" * 80)

    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # Query grid cells with scores
        sql = text("""
            SELECT
                gc.id,
                gc.lon,
                gc.lat,
                gc.grid_x,
                gc.grid_y,
                COALESCE(mo.final_score, 0.5) as score,
                COALESCE(mo.score_class, 'unknown') as score_class
            FROM grid_cells gc
            LEFT JOIN model_outputs mo ON gc.id = mo.grid_cell_id
            WHERE gc.basin_id = :basin_id
            ORDER BY gc.grid_x, gc.grid_y
        """)

        results = session.execute(sql, {"basin_id": basin_id}).fetchall()

        # Create grid heatmap GeoJSON
        grid_size = 0.5  # degrees

        features = []
        for row in results:
            lon, lat = row[1], row[2]

            # Create polygon for grid cell
            coords = [
                [lon, lat],
                [lon + grid_size, lat],
                [lon + grid_size, lat + grid_size],
                [lon, lat + grid_size],
                [lon, lat]
            ]

            # Color-code by score
            score = float(row[5])
            if score > 0.75:
                color = "#d94848"  # Red - High
            elif score > 0.5:
                color = "#d89a00"  # Orange - Medium
            else:
                color = "#087f8c"  # Teal - Low

            feature = {
                "type": "Feature",
                "properties": {
                    "id": str(row[0]),
                    "prospectivity_score": score,
                    "score_class": row[6],
                    "grid_x": row[3],
                    "grid_y": row[4],
                    "color": color,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            }
            features.append(feature)

        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        output_file = TILES_DIR / "heatmap_grid.geojson"
        with open(output_file, "w") as f:
            json.dump(geojson, f, indent=2)

        logger.info(f"✅ Created heatmap for {len(features)} grid cells")
        logger.info(f"   Saved to: {output_file}")

    return True

def step_4_export_source_data_layers(basin_id: str):
    """Export source geospatial layers (faults, heat flow, etc.)"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("STEP 4: EXPORT SOURCE DATA LAYERS (Faults, Heat Flow, Geology)")
    logger.info("=" * 80)

    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # Export faults
        faults_sql = text("""
            SELECT id, fault_name, fault_type, confidence
            FROM faults
            WHERE basin_id = :basin_id
        """)

        faults = session.execute(faults_sql, {"basin_id": basin_id}).fetchall()

        fault_features = []
        for fault in faults:
            feature = {
                "type": "Feature",
                "properties": {
                    "id": str(fault[0]),
                    "name": fault[1],
                    "fault_type": fault[2],
                    "confidence": float(fault[3]) if fault[3] else 0.5,
                },
                "geometry": {"type": "LineString", "coordinates": []}
            }
            fault_features.append(feature)

        faults_geojson = {"type": "FeatureCollection", "features": fault_features}
        with open(TILES_DIR / "faults.geojson", "w") as f:
            json.dump(faults_geojson, f, indent=2)

        logger.info(f"✅ Exported {len(faults)} faults")

        # Export heat flow points
        heatflow_sql = text("""
            SELECT id, heatflow_mwm2
            FROM heatflow_points
            WHERE basin_id = :basin_id
        """)

        heatflows = session.execute(heatflow_sql, {"basin_id": basin_id}).fetchall()

        heatflow_features = []
        for hf in heatflows:
            feature = {
                "type": "Feature",
                "properties": {
                    "id": str(hf[0]),
                    "heatflow_mw_m2": float(hf[1]) if hf[1] else 60.0,
                },
                "geometry": {"type": "Point", "coordinates": []}
            }
            heatflow_features.append(feature)

        heatflow_geojson = {"type": "FeatureCollection", "features": heatflow_features}
        with open(TILES_DIR / "heatflow_points.geojson", "w") as f:
            json.dump(heatflow_geojson, f, indent=2)

        logger.info(f"✅ Exported {len(heatflows)} heat flow points")

    return True

def step_5_create_tile_metadata():
    """Create tile metadata and index"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("STEP 5: CREATE TILE METADATA")
    logger.info("=" * 80)

    # List all tiles
    tiles = list(TILES_DIR.glob("*.geojson"))

    metadata = {
        "tiles": {
            "model_outputs": {
                "file": "model_outputs.geojson",
                "description": "Prospectivity scores and rankings for all grid cells",
                "layers": ["points"],
                "feature_count": 0,
            },
            "heatmap_grid": {
                "file": "heatmap_grid.geojson",
                "description": "Grid-based heatmap visualization of prospectivity",
                "layers": ["grid"],
                "feature_count": 0,
            },
            "prospect_zones": {
                "file": "prospect_zones.geojson",
                "description": "Clustered prospect zones with aggregated scores",
                "layers": ["zones"],
                "feature_count": 0,
            },
            "faults": {
                "file": "faults.geojson",
                "description": "Fault lines and structural features",
                "layers": ["lines"],
                "feature_count": 0,
            },
            "heatflow_points": {
                "file": "heatflow_points.geojson",
                "description": "Heat flow measurement points and interpolation",
                "layers": ["points"],
                "feature_count": 0,
            },
        },
        "vector_tile_info": {
            "format": "GeoJSON (MVT-compatible)",
            "projection": "EPSG:4326 (WGS84)",
            "browser_compatible": True,
            "usage": "Load in MapLibre with GeoJSON sources",
        },
        "rendering_suggestions": {
            "prospectivity_color_scale": {
                "high": {"score_range": [0.75, 1.0], "color": "#d94848"},
                "medium": {"score_range": [0.5, 0.75], "color": "#d89a00"},
                "low": {"score_range": [0.0, 0.5], "color": "#087f8c"},
            },
        },
    }

    # Count features in each tile
    for tile_key, tile_info in metadata["tiles"].items():
        tile_file = TILES_DIR / tile_info["file"]
        if tile_file.exists():
            with open(tile_file, "r") as f:
                geojson = json.load(f)
                metadata["tiles"][tile_key]["feature_count"] = len(geojson.get("features", []))

    metadata_file = TILES_DIR / "tiles_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"✅ Created tile metadata")
    logger.info(f"   Saved to: {metadata_file}")

    # Summary
    logger.info("")
    logger.info("Tiles Summary:")
    for tile_key, tile_info in metadata["tiles"].items():
        logger.info(f"   • {tile_key:20s} ({tile_info['feature_count']:3d} features)")

    return True

def main():
    logger.info("")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 25 + "PHASE 2: VECTOR TILE GENERATION" + " " * 22 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("")
    logger.info(f"Tiles directory: {TILES_DIR}")
    logger.info("")

    # Get latest basin
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        basin_sql = text("SELECT id, name FROM basins ORDER BY created_at DESC LIMIT 1")
        basin = session.execute(basin_sql).fetchone()
        if not basin:
            logger.error("No basin found")
            return False
        basin_id = str(basin[0])

    logger.info(f"Processing basin: {basin[1]}")
    logger.info("")

    steps = [
        ("Export GeoJSON Tiles", lambda: step_1_export_geojson_tiles(basin_id)),
        ("Export Prospect Zones", lambda: step_2_export_zones_geojson(basin_id)),
        ("Create Heatmap Tiles", lambda: step_3_create_heatmap_tiles(basin_id)),
        ("Export Source Layers", lambda: step_4_export_source_data_layers(basin_id)),
        ("Create Metadata", lambda: step_5_create_tile_metadata()),
    ]

    for step_name, step_func in steps:
        try:
            if not step_func():
                logger.error(f"❌ {step_name} failed")
                return False
        except Exception as e:
            logger.error(f"❌ {step_name} error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ PHASE 2 COMPLETE: Vector Tiles Generated")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"Tiles saved to: {TILES_DIR}")
    logger.info("")
    logger.info("Generated tiles:")
    logger.info("  • model_outputs.geojson    — Prospectivity scores (points)")
    logger.info("  • heatmap_grid.geojson     — Grid heatmap (polygons)")
    logger.info("  • prospect_zones.geojson   — Prospect zones (clustered)")
    logger.info("  • faults.geojson           — Fault lines")
    logger.info("  • heatflow_points.geojson  — Heat flow measurements")
    logger.info("  • tiles_metadata.json      — Metadata & rendering hints")
    logger.info("")
    logger.info("Usage:")
    logger.info("  1. Load tiles in MapLibre: map.addSource('prospects', {...geojson...})")
    logger.info("  2. Style with color scale based on prospectivity_score")
    logger.info("  3. Interactive: click cells to see details")
    logger.info("")

    return True

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
