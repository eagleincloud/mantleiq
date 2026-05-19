"""
Zone detail endpoints.
Get zone information, scores, attribution, and comparisons.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
import logging
import json

from app.core.database import get_db
from app.models.schemas import (
    ZoneDetailResponse, ZoneScoreComponents, FeatureContribution,
    CompareZonesRequest, ComparisonResult
)
from app.models.orm import ModelOutputsORM, FeaturesORM, ZonesORM

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zones", tags=["zones"])


def _interpret_score(score: float) -> str:
    """Map score to interpretation class."""
    if score >= 80:
        return "High-priority target"
    elif score >= 65:
        return "Strong prospect, needs validation"
    elif score >= 50:
        return "Moderate prospect"
    elif score >= 35:
        return "Weak / speculative"
    else:
        return "Low priority"


def _get_zone_detail(zone_id: str, db: Session) -> ZoneDetailResponse:
    """
    Internal helper to fetch and format zone details.
    """
    # Query zone
    zone = db.query(ZonesORM).filter(ZonesORM.id == zone_id).first()
    if not zone:
        return None

    # Query model output (scoring results)
    model_output = db.query(ModelOutputsORM).filter(
        ModelOutputsORM.zone_id == zone_id
    ).first()

    if not model_output:
        # Return zone without scores
        return ZoneDetailResponse(
            id=str(zone.id),
            name=zone.name or f"Zone {zone_id[:8]}",
            rank=0,
            centroid=[0, 0],
            prospectivity_score=0.0,
            confidence_score=0.5,
            score_class="Not scored",
            components=ZoneScoreComponents(
                f_generation=0.0,
                f_fluid_interaction=0.0,
                f_structural_pathways=0.0,
                f_trap_retention=0.0,
                f_surface_indicators=0.0,
                f_thermodynamic=0.0,
            ),
            top_features=[],
            missing_data_caveats=["Zone has not been scored yet"],
            explanation_summary="This zone is pending analysis.",
            recommended_next_actions=["Run analysis for this basin"],
        )

    # Extract centroid from zone geometry (simplified: use a default)
    centroid = [0.0, 0.0]  # Phase 2: extract from ST_Centroid(geometry)

    # Score components (stored as JSONB in database)
    components_dict = model_output.components or {}
    components = ZoneScoreComponents(
        f_generation=components_dict.get("f_generation", 0.0),
        f_fluid_interaction=components_dict.get("f_fluid_interaction", 0.0),
        f_structural_pathways=components_dict.get("f_structural_pathways", 0.0),
        f_trap_retention=components_dict.get("f_trap_retention", 0.0),
        f_surface_indicators=components_dict.get("f_surface_indicators", 0.0),
        f_thermodynamic=components_dict.get("f_thermodynamic", 0.0),
    )

    # Top features from attribution
    top_features = []
    if model_output.top_features:
        for feature in model_output.top_features[:4]:
            top_features.append(FeatureContribution(
                name=feature.get("name", "unknown"),
                label=feature.get("label", "Unknown"),
                value=feature.get("value", 0.0),
                weight=feature.get("weight", 0.0),
                contribution=feature.get("contribution", 0.0),
            ))

    # Data quality caveats
    missing_data_caveats = []
    if model_output.confidence_score < 0.7:
        missing_data_caveats.append("Limited data coverage in this region")
    if model_output.confidence_score < 0.6:
        missing_data_caveats.append("Some critical data layers missing")

    return ZoneDetailResponse(
        id=str(zone.id),
        name=zone.name or f"Zone {zone_id[:8]}",
        rank=model_output.rank or 0,
        centroid=centroid,
        prospectivity_score=round(model_output.final_score * 100, 1),
        confidence_score=model_output.confidence_score,
        score_class=_interpret_score(model_output.final_score * 100),
        components=components,
        top_features=top_features,
        missing_data_caveats=missing_data_caveats,
        explanation_summary=model_output.explanation_summary or "Zone scoring complete",
        recommended_next_actions=["Conduct field survey", "Acquire additional seismic data"],
    )


@router.get("/{zone_id}", response_model=ZoneDetailResponse)
async def get_zone(zone_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific zone.

    Args:
        zone_id: Zone UUID

    Returns:
        Zone details with scores, components, attribution, and explanations
    """
    try:
        zone_detail = _get_zone_detail(zone_id, db)

        if zone_detail is None:
            raise HTTPException(status_code=404, detail="Zone not found")

        return zone_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving zone {zone_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve zone")


@router.post("/compare", response_model=ComparisonResult)
async def compare_zones(
    request: CompareZonesRequest,
    db: Session = Depends(get_db),
):
    """
    Compare multiple zones side-by-side.

    Args:
        request: List of zone IDs to compare (2-10 zones)

    Returns:
        Comparison with all zones and summary
    """
    try:
        zones_detail = []

        for zone_id in request.zone_ids:
            zone_detail = _get_zone_detail(zone_id, db)
            if zone_detail:
                zones_detail.append(zone_detail)
            else:
                logger.warning(f"Zone {zone_id} not found in comparison")

        if not zones_detail:
            raise HTTPException(status_code=404, detail="No zones found for comparison")

        # Generate comparison summary
        sorted_zones = sorted(zones_detail, key=lambda z: z.prospectivity_score, reverse=True)
        top_zone = sorted_zones[0]
        summary = f"Top zone: {top_zone.name} ({top_zone.prospectivity_score:.1f}). "
        summary += f"Comparing {len(zones_detail)} zones across key factors."

        return ComparisonResult(
            zones=zones_detail,
            summary=summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing zones: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare zones")


@router.get("", response_model=list[ZoneDetailResponse])
async def list_basin_zones(basin_id: str, db: Session = Depends(get_db)):
    """
    List all zones in a basin (ordered by score).

    Args:
        basin_id: Basin UUID

    Returns:
        List of zones for the basin, sorted by prospectivity score (descending)
    """
    try:
        # Query zones for basin
        zones = db.query(ZonesORM).filter(ZonesORM.basin_id == basin_id).all()

        if not zones:
            return []

        zone_details = []
        for zone in zones:
            zone_detail = _get_zone_detail(str(zone.id), db)
            if zone_detail:
                zone_details.append(zone_detail)

        # Sort by prospectivity score descending
        zone_details.sort(key=lambda z: z.prospectivity_score, reverse=True)

        return zone_details

    except Exception as e:
        logger.error(f"Error listing zones for basin {basin_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve zones")
