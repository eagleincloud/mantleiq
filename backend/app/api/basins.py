"""
Basin management endpoints.
List available basins and get basin details.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
import logging

from app.core.database import get_db
from app.models.schemas import BasinResponse, BasinCreate
from app.models.orm import BasinORM, DataLayersORM

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/basins", tags=["basins"])


@router.get("", response_model=list[BasinResponse])
async def list_basins(db: Session = Depends(get_db)):
    """
    List all available basins.

    Returns:
        List of basin summaries with data coverage scores
    """
    try:
        # Query all basins
        basins = db.query(BasinORM).all()

        if not basins:
            return []

        # Compute data coverage for each basin
        results = []
        for basin in basins:
            # Count available data layers for this basin
            layer_count = db.query(func.count(DataLayersORM.id)).filter(
                DataLayersORM.basin_id == basin.id,
                DataLayersORM.curated_uri.isnot(None)
            ).scalar()

            # Expected layers: 8 (Macrostrat, USGS, NOAA gravity, NOAA magnetic, IHFC, SRTM, GLiM, surface indicators)
            expected_layers = 8
            coverage_score = min(1.0, layer_count / expected_layers) if expected_layers > 0 else 0.0

            basin_response = BasinResponse(
                id=str(basin.id),
                name=basin.name,
                region=basin.region,
                country=basin.country,
                data_coverage_score=coverage_score,
                created_at=basin.created_at,
            )
            results.append(basin_response)

        return results

    except Exception as e:
        logger.error(f"Error listing basins: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve basins")


@router.get("/{basin_id}", response_model=BasinResponse)
async def get_basin(basin_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific basin.

    Args:
        basin_id: Basin UUID

    Returns:
        Basin details with data coverage score
    """
    try:
        # Query basin
        basin = db.query(BasinORM).filter(BasinORM.id == basin_id).first()

        if not basin:
            raise HTTPException(status_code=404, detail="Basin not found")

        # Compute data coverage
        layer_count = db.query(func.count(DataLayersORM.id)).filter(
            DataLayersORM.basin_id == basin.id,
            DataLayersORM.curated_uri.isnot(None)
        ).scalar()

        expected_layers = 8
        coverage_score = min(1.0, layer_count / expected_layers) if expected_layers > 0 else 0.0

        return BasinResponse(
            id=str(basin.id),
            name=basin.name,
            region=basin.region,
            country=basin.country,
            data_coverage_score=coverage_score,
            created_at=basin.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving basin {basin_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve basin")


@router.post("", response_model=BasinResponse, status_code=201)
async def create_basin(basin: BasinCreate, db: Session = Depends(get_db)):
    """
    Create a new basin (admin only).

    Args:
        basin: Basin data

    Returns:
        Created basin with UUID
    """
    try:
        # Check if basin name already exists
        existing = db.query(BasinORM).filter(BasinORM.name == basin.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Basin name already exists")

        # Create new basin
        new_basin = BasinORM(
            name=basin.name,
            region=basin.region,
            country=basin.country,
            description=basin.description,
        )

        db.add(new_basin)
        db.commit()
        db.refresh(new_basin)

        return BasinResponse(
            id=str(new_basin.id),
            name=new_basin.name,
            region=new_basin.region,
            country=new_basin.country,
            data_coverage_score=0.0,
            created_at=new_basin.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating basin: {e}")
        raise HTTPException(status_code=500, detail="Failed to create basin")
