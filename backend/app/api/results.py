"""
Results and tiles endpoints.
Get analysis results and serve vector tiles for web visualization.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import json
from pathlib import Path

from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["results"])

# Local tiles directory
TILES_DIR = Path("/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/local_storage/tiles")


@router.get("/results/{basin_id}")
async def get_basin_results(basin_id: str, db: Session = Depends(get_db)):
    """
    Get all model outputs (scores) for a basin as GeoJSON.

    Args:
        basin_id: Basin UUID

    Returns:
        GeoJSON FeatureCollection with scored grid cells
    """
    logger.info(f"DEBUG: /results/{basin_id} endpoint called - NEW GeoJSON code")
    try:
        # Query model outputs with polygon geometries
        sql = text("""
            SELECT
                mo.id,
                mo.grid_cell_id,
                mo.final_score,
                mo.confidence_score,
                ROW_NUMBER() OVER (ORDER BY mo.final_score DESC) as rank,
                mo.score_class,
                mo.f_generation,
                mo.f_fluid_interaction,
                mo.f_structural_pathways,
                mo.f_trap_retention,
                mo.f_surface_indicators,
                mo.f_thermodynamic,
                gc.lat,
                gc.lon,
                gc.grid_x,
                gc.grid_y,
                ST_AsGeoJSON(gc.geometry) as geometry_geojson
            FROM model_outputs mo
            JOIN grid_cells gc ON mo.grid_cell_id = gc.id
            WHERE mo.basin_id = :basin_id
            ORDER BY mo.final_score DESC
        """)

        results = db.execute(sql, {"basin_id": basin_id}).fetchall()

        if not results:
            return {
                "type": "FeatureCollection",
                "features": [],
                "properties": {
                    "basin_id": basin_id,
                    "total_count": 0,
                    "top_score": 0.0,
                    "avg_score": 0.0,
                }
            }

        # Format as GeoJSON FeatureCollection
        features = []
        scores = []

        for row in results:
            score = float(row[2])
            scores.append(score)

            geometry = json.loads(row[16])

            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "id": str(row[0]),
                    "grid_cell_id": str(row[1]),
                    "prospectivity_score": score,
                    "confidence": float(row[3]),
                    "rank": int(row[4]),
                    "score_class": row[5],
                    "f_generation": float(row[6]) if row[6] else 0,
                    "f_fluid_interaction": float(row[7]) if row[7] else 0,
                    "f_structural_pathways": float(row[8]) if row[8] else 0,
                    "f_trap_retention": float(row[9]) if row[9] else 0,
                    "f_surface_indicators": float(row[10]) if row[10] else 0,
                    "f_thermodynamic": float(row[11]) if row[11] else 0,
                    "lat": float(row[12]),
                    "lon": float(row[13]),
                    "grid_x": row[14],
                    "grid_y": row[15],
                }
            }
            features.append(feature)

        avg_score = sum(scores) / len(scores) if scores else 0.0

        return {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "basin_id": basin_id,
                "total_count": len(features),
                "top_score": max(scores) if scores else 0.0,
                "avg_score": avg_score,
            }
        }

    except Exception as e:
        logger.error(f"Error retrieving results for basin {basin_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve results")


@router.get("/tiles/{layer}")
async def get_tile(layer: str):
    """
    Get vector tile in GeoJSON format.

    Args:
        layer: Tile layer name (model_outputs, heatmap_grid, prospect_zones, faults, heatflow_points)

    Returns:
        GeoJSON FeatureCollection
    """
    try:
        # Map layer names to files
        layer_files = {
            "model_outputs": "model_outputs.geojson",
            "heatmap_grid": "heatmap_grid.geojson",
            "prospect_zones": "prospect_zones.geojson",
            "faults": "faults.geojson",
            "heatflow_points": "heatflow_points.geojson",
        }

        if layer not in layer_files:
            raise HTTPException(
                status_code=404,
                detail=f"Tile layer '{layer}' not found. Available: {list(layer_files.keys())}",
            )

        tile_file = TILES_DIR / layer_files[layer]

        if not tile_file.exists():
            raise HTTPException(status_code=404, detail=f"Tile file not found: {layer}")

        # Load and return GeoJSON
        with open(tile_file, "r") as f:
            geojson = json.load(f)

        return JSONResponse(content=geojson)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving tile {layer}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tile")


@router.get("/tiles/metadata.json")
async def get_tiles_metadata():
    """
    Get metadata about available tiles.

    Returns:
        Tile metadata with rendering hints and feature counts
    """
    try:
        metadata_file = TILES_DIR / "tiles_metadata.json"

        if not metadata_file.exists():
            return {
                "message": "No tile metadata available",
                "tiles": {},
            }

        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        return metadata

    except Exception as e:
        logger.error(f"Error retrieving tile metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tile metadata")
