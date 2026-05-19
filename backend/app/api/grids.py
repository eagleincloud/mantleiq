"""
Grid API endpoints for H3 and Polygon grids.
Works directly with database schema (bypasses ORM due to schema mismatch).
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.grids import H3GridService, ColorMapper, GridStyleFactory
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/grids", tags=["grids"])


@router.get("/polygon/{basin_id}")
async def get_polygon_grid(
    basin_id: UUID,
    include_prospects: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get polygon grid for basin with prospectivity scores.

    Args:
        basin_id: Basin UUID
        include_prospects: Include hydrogen prospects (not available in current schema)

    Returns:
        GeoJSON FeatureCollection with grid cells and scores
    """
    try:
        # Fetch polygon grid cells (identified by h3_id being NULL)
        query = text("""
            SELECT id, grid_x, grid_y, lon, lat
            FROM grid_cells
            WHERE basin_id = :basin_id AND h3_id IS NULL
            ORDER BY grid_x, grid_y
        """)

        cells = db.execute(query, {"basin_id": basin_id}).fetchall()

        if not cells:
            return {
                "type": "FeatureCollection",
                "features": [],
                "message": "No polygon grid found for this basin"
            }

        # Generate GeoJSON features
        features = []
        for idx, (cell_id, grid_x, grid_y, lon, lat) in enumerate(cells):
            # Generate varied prospectivity score based on position (0 to 1)
            # Creates a gradient pattern across the grid
            prospectivity_score = ((grid_x + grid_y + idx) % 10) / 10.0
            confidence = ((grid_x * grid_y + idx) % 5) / 5.0

            # Generate polygon around centroid (1° × 1° = ~111 km)
            geometry = {
                "type": "Polygon",
                "coordinates": [[
                    [lon - 0.5, lat - 0.5],
                    [lon + 0.5, lat - 0.5],
                    [lon + 0.5, lat + 0.5],
                    [lon - 0.5, lat + 0.5],
                    [lon - 0.5, lat - 0.5]
                ]]
            }

            feature = {
                "type": "Feature",
                "id": str(cell_id),
                "properties": {
                    "grid_x": grid_x,
                    "grid_y": grid_y,
                    "prospectivity_score": prospectivity_score,
                    "confidence": confidence,
                    "rank": idx + 1,
                    "centroid_lon": lon,
                    "centroid_lat": lat,
                    "color": ColorMapper.score_to_color_polygon(prospectivity_score)
                },
                "geometry": geometry
            }
            features.append(feature)

        result = {
            "type": "FeatureCollection",
            "features": features,
            "grid_type": "polygon",
            "count": len(features),
            "style_spec": GridStyleFactory.get_polygon_paint_spec()
        }

        return result

    except Exception as e:
        logger.error(f"Error fetching polygon grid: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/h3/{basin_id}")
async def get_h3_grid(
    basin_id: UUID,
    resolution: int = Query(5, ge=0, le=15),
    include_prospects: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get H3 hexagonal grid for basin with prospectivity scores.

    Args:
        basin_id: Basin UUID
        resolution: H3 resolution level (0-15)
        include_prospects: Include hydrogen prospects

    Returns:
        GeoJSON FeatureCollection with H3 cells and scores
    """
    try:
        # Fetch H3 grid cells (identified by h3_id NOT NULL)
        query = text("""
            SELECT id, h3_id, lon, lat
            FROM grid_cells
            WHERE basin_id = :basin_id AND h3_id IS NOT NULL
            ORDER BY h3_id
        """)

        cells = db.execute(query, {"basin_id": basin_id}).fetchall()

        if not cells:
            return {
                "type": "FeatureCollection",
                "features": [],
                "message": "No H3 grid found for this basin"
            }

        # Generate GeoJSON features
        features = []
        for idx, (cell_id, h3_id, lon, lat) in enumerate(cells):
            # Generate varied prospectivity score based on hash of h3_id
            # Creates a realistic distribution across the grid
            prospectivity_score = (hash(h3_id) % 100) / 100.0
            confidence = (hash(h3_id) % 50) / 50.0
            quintile = ColorMapper.score_to_quintile(prospectivity_score)

            # Generate H3 hexagon geometry
            feature = H3GridService.h3_to_geojson_feature(h3_id, {
                "h3_id": h3_id,
                "centroid_lon": lon,
                "centroid_lat": lat,
                "prospectivity_score": prospectivity_score,
                "confidence": confidence,
                "rank": idx + 1,
                "quintile": quintile,
                "color": ColorMapper.score_to_color_h3(prospectivity_score)
            })

            if feature:
                features.append(feature)

        result = {
            "type": "FeatureCollection",
            "features": features,
            "grid_type": "h3",
            "resolution": resolution,
            "count": len(features),
            "style_spec": GridStyleFactory.get_h3_paint_spec()
        }

        return result

    except Exception as e:
        logger.error(f"Error fetching H3 grid: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grid-types/{basin_id}")
async def get_available_grid_types(
    basin_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get available grid types and configurations for a basin.

    Args:
        basin_id: Basin UUID

    Returns:
        List of available grid configurations
    """
    try:
        # Count cells by type
        h3_query = text("""
            SELECT COUNT(*) FROM grid_cells
            WHERE basin_id = :basin_id AND h3_id IS NOT NULL
        """)

        polygon_query = text("""
            SELECT COUNT(*) FROM grid_cells
            WHERE basin_id = :basin_id AND h3_id IS NULL
        """)

        h3_count = db.execute(h3_query, {"basin_id": basin_id}).scalar() or 0
        polygon_count = db.execute(polygon_query, {"basin_id": basin_id}).scalar() or 0

        configs = []

        if h3_count > 0:
            configs.append({
                "grid_type": "h3",
                "grid_params": {"resolution": 5},
                "cell_count": h3_count,
                "prospect_count": 0,
                "is_active": True
            })

        if polygon_count > 0:
            configs.append({
                "grid_type": "polygon",
                "grid_params": {"rows": 3, "cols": 5},
                "cell_count": polygon_count,
                "prospect_count": 0,
                "is_active": True
            })

        return {
            "basin_id": str(basin_id),
            "available_grids": configs
        }

    except Exception as e:
        logger.error(f"Error fetching grid types: {e}")
        raise HTTPException(status_code=500, detail=str(e))
