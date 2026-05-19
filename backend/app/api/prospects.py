"""
Hydrogen prospects API endpoints.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/prospects", tags=["prospects"])


class ProspectCreate(BaseModel):
    """Request schema for creating prospect"""
    grid_cell_id: UUID
    basin_id: UUID
    longitude: float
    latitude: float
    prospect_type: Optional[str] = None
    significance_score: Optional[float] = None
    h3_id: Optional[str] = None
    description: Optional[str] = None


class ProspectResponse(BaseModel):
    """Response schema for prospect"""
    id: UUID
    grid_cell_id: UUID
    basin_id: UUID
    longitude: float
    latitude: float
    prospect_type: Optional[str]
    significance_score: Optional[float]
    h3_id: Optional[str]
    description: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.get("/{basin_id}")
async def get_basin_prospects(
    basin_id: UUID,
    grid_type: Optional[str] = Query(None, description="Filter by 'polygon' or 'h3'"),
    db: Session = Depends(get_db)
) -> List[dict]:
    """
    Get all hydrogen prospects for a basin.

    Args:
        basin_id: Basin UUID
        grid_type: Optional filter for grid type

    Returns:
        GeoJSON FeatureCollection with prospect locations
    """
    try:
        query = db.query(HydrogenProspectsORM).filter(
            HydrogenProspectsORM.basin_id == basin_id
        )

        if grid_type == "polygon":
            query = query.filter(HydrogenProspectsORM.h3_id.is_(None))
        elif grid_type == "h3":
            query = query.filter(HydrogenProspectsORM.h3_id.isnot(None))

        prospects = query.all()

        features = []
        for prospect in prospects:
            feature = {
                "type": "Feature",
                "id": str(prospect.id),
                "properties": {
                    "prospect_id": str(prospect.id),
                    "grid_cell_id": str(prospect.grid_cell_id),
                    "h3_id": prospect.h3_id,
                    "prospect_type": prospect.prospect_type or "unknown",
                    "significance_score": prospect.significance_score or 50,
                    "description": prospect.description,
                    "created_at": prospect.created_at.isoformat()
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [prospect.longitude, prospect.latitude]
                }
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features,
            "count": len(features)
        }

    except Exception as e:
        logger.error(f"Error fetching prospects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{basin_id}")
async def create_prospect(
    basin_id: UUID,
    prospect: ProspectCreate,
    db: Session = Depends(get_db)
) -> dict:
    """
    Create a new hydrogen prospect.

    Args:
        basin_id: Basin UUID
        prospect: Prospect data

    Returns:
        Created prospect
    """
    try:
        # Verify grid cell exists
        cell = db.query(GridCellsORM).filter(
            GridCellsORM.id == prospect.grid_cell_id
        ).first()

        if not cell:
            raise HTTPException(status_code=404, detail="Grid cell not found")

        # Create prospect
        new_prospect = HydrogenProspectsORM(
            grid_cell_id=prospect.grid_cell_id,
            basin_id=basin_id,
            longitude=prospect.longitude,
            latitude=prospect.latitude,
            prospect_type=prospect.prospect_type,
            significance_score=prospect.significance_score,
            h3_id=prospect.h3_id,
            description=prospect.description
        )

        db.add(new_prospect)
        db.commit()
        db.refresh(new_prospect)

        return {
            "id": str(new_prospect.id),
            "grid_cell_id": str(new_prospect.grid_cell_id),
            "basin_id": str(new_prospect.basin_id),
            "longitude": new_prospect.longitude,
            "latitude": new_prospect.latitude,
            "prospect_type": new_prospect.prospect_type,
            "significance_score": new_prospect.significance_score,
            "h3_id": new_prospect.h3_id,
            "created_at": new_prospect.created_at.isoformat(),
            "message": "Prospect created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating prospect: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grid-cell/{cell_id}", response_model=None)
async def get_cell_prospects(
    cell_id: UUID,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get all prospects within a specific grid cell.

    Args:
        cell_id: Grid cell UUID

    Returns:
        GeoJSON FeatureCollection with prospects in this cell
    """
    try:
        prospects = db.query(HydrogenProspectsORM).filter(
            HydrogenProspectsORM.grid_cell_id == cell_id
        ).all()

        features = []
        for prospect in prospects:
            feature = {
                "type": "Feature",
                "id": str(prospect.id),
                "properties": {
                    "prospect_type": prospect.prospect_type or "unknown",
                    "significance_score": prospect.significance_score or 50
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [prospect.longitude, prospect.latitude]
                }
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features,
            "count": len(features)
        }

    except Exception as e:
        logger.error(f"Error fetching cell prospects: {e}")
        raise HTTPException(status_code=500, detail=str(e))
