"""
Data layers endpoints.
Get metadata about available and missing data layers for basins and cells.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-layers", tags=["data-layers"])

# Define all expected data layers with metadata
EXPECTED_LAYERS = {
    "gravity": {
        "name": "Gravity Anomaly",
        "description": "Bouguer gravity anomaly from NOAA/NCEI",
        "type": "raster",
        "resolution": "2 km",
        "critical": True,
        "weight": 0.15
    },
    "magnetic": {
        "name": "Magnetic Field",
        "description": "Total magnetic intensity from NOAA EMAG2",
        "type": "raster",
        "resolution": "2 km",
        "critical": True,
        "weight": 0.15
    },
    "geology": {
        "name": "Geological Units",
        "description": "Lithology and stratigraphic units from Macrostrat",
        "type": "vector",
        "resolution": "1:100k",
        "critical": True,
        "weight": 0.20
    },
    "faults": {
        "name": "Fault Lines",
        "description": "Quaternary and mapped faults from USGS",
        "type": "vector",
        "resolution": "1:100k",
        "critical": True,
        "weight": 0.15
    },
    "seismic": {
        "name": "Seismic Interpretation",
        "description": "3D/2D seismic horizons and sections",
        "type": "vector",
        "resolution": "Variable",
        "critical": True,
        "weight": 0.20
    },
    "wells": {
        "name": "Well Logs & Cores",
        "description": "Borehole data, lithology logs, and core analysis",
        "type": "point",
        "resolution": "Sparse",
        "critical": True,
        "weight": 0.10
    },
    "heatflow": {
        "name": "Heat Flow Data",
        "description": "Geothermal gradient measurements from IHFC",
        "type": "point",
        "resolution": "Sparse",
        "critical": False,
        "weight": 0.05
    },
    "dem": {
        "name": "Digital Elevation Model",
        "description": "SRTM or GEBCO DEM for topography",
        "type": "raster",
        "resolution": "30-90 m",
        "critical": False,
        "weight": 0.05
    }
}


@router.get("/basins/{basin_id}")
async def get_basin_data_layers(basin_id: str, db: Session = Depends(get_db)):
    """
    Get available and missing data layers for a basin.

    Args:
        basin_id: Basin UUID

    Returns:
        Data layer information with availability status
    """
    try:
        # Query available layers from data_layers table
        sql = text("""
            SELECT
                name,
                source_name,
                layer_type,
                resolution,
                acquisition_date,
                source_confidence,
                data_quality
            FROM data_layers
            WHERE basin_id = :basin_id
            ORDER BY created_at DESC
        """)

        results = db.execute(sql, {"basin_id": basin_id}).fetchall()

        available_layers = {}
        for row in results:
            available_layers[row[0].lower()] = {
                "name": row[0],
                "source": row[1],
                "type": row[2],
                "resolution": row[3],
                "date": str(row[4]) if row[4] else None,
                "confidence": float(row[5]) if row[5] else 0.8,
                "quality": float(row[6]) if row[6] else 0.8,
                "available": True
            }

        # Compile list of available and missing
        available = []
        missing = []

        for layer_key, layer_info in EXPECTED_LAYERS.items():
            if layer_key in available_layers:
                available.append({
                    "key": layer_key,
                    "name": layer_info["name"],
                    "description": layer_info["description"],
                    "available": True,
                    "critical": layer_info["critical"],
                    "weight": layer_info["weight"],
                    "metadata": available_layers[layer_key]
                })
            else:
                missing.append({
                    "key": layer_key,
                    "name": layer_info["name"],
                    "description": layer_info["description"],
                    "available": False,
                    "critical": layer_info["critical"],
                    "weight": layer_info["weight"]
                })

        # Calculate data completeness score
        critical_available = sum(1 for l in available if l["critical"])
        critical_expected = sum(1 for l in EXPECTED_LAYERS.values() if l["critical"])
        completeness = critical_available / critical_expected if critical_expected > 0 else 0.0

        # Calculate weighted completeness
        available_weight = sum(l["weight"] for l in available)
        total_weight = sum(l["weight"] for l in EXPECTED_LAYERS.values())
        weighted_completeness = available_weight / total_weight if total_weight > 0 else 0.0

        return {
            "basin_id": basin_id,
            "available_layers": available,
            "missing_layers": missing,
            "completeness_metrics": {
                "critical_layers_available": critical_available,
                "critical_layers_expected": critical_expected,
                "completeness_percentage": completeness * 100,
                "weighted_completeness": weighted_completeness * 100
            },
            "confidence_impact": _calculate_confidence_impact(missing),
            "recommendations": _get_data_acquisition_recommendations(missing)
        }

    except Exception as e:
        logger.error(f"Error retrieving data layers for basin {basin_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve data layers")


@router.get("/cells/{cell_id}")
async def get_cell_data_coverage(cell_id: str, db: Session = Depends(get_db)):
    """
    Get data coverage information for a specific grid cell.

    Args:
        cell_id: Grid cell UUID

    Returns:
        Data coverage and completeness for the cell
    """
    try:
        # Query features table for data quality metrics
        sql = text("""
            SELECT
                data_coverage,
                data_quality,
                missing_data_completeness,
                confidence_modifier
            FROM features
            WHERE grid_cell_id = :cell_id
            LIMIT 1
        """)

        result = db.execute(sql, {"cell_id": cell_id}).fetchone()

        if not result:
            # Return default if no features yet
            return {
                "cell_id": cell_id,
                "data_coverage": 0.0,
                "data_quality": 0.0,
                "missing_data_completeness": 0.0,
                "confidence_modifier": 0.5,
                "assessment": "Insufficient data"
            }

        coverage, quality, missing_completeness, confidence_mod = result

        assessment = _assess_data_completeness(
            coverage, quality, missing_completeness
        )

        return {
            "cell_id": cell_id,
            "data_coverage": float(coverage) if coverage else 0.0,
            "data_quality": float(quality) if quality else 0.0,
            "missing_data_completeness": float(missing_completeness) if missing_completeness else 0.0,
            "confidence_modifier": float(confidence_mod) if confidence_mod else 0.5,
            "assessment": assessment,
            "confidence_penalty": (1.0 - float(confidence_mod)) * 100 if confidence_mod else 50.0
        }

    except Exception as e:
        logger.error(f"Error retrieving data coverage for cell {cell_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve data coverage")


# Helper functions
def _calculate_confidence_impact(missing_layers):
    """Calculate how much confidence is reduced due to missing layers"""
    if not missing_layers:
        return {
            "penalty_percentage": 0,
            "impact_level": "None",
            "explanation": "All critical data layers available"
        }

    critical_missing = [l for l in missing_layers if l["critical"]]

    if len(critical_missing) >= 3:
        return {
            "penalty_percentage": 30,
            "impact_level": "HIGH",
            "explanation": f"{len(critical_missing)} critical data layers missing. Score confidence significantly reduced."
        }
    elif len(critical_missing) >= 1:
        return {
            "penalty_percentage": 15,
            "impact_level": "MODERATE",
            "explanation": f"{len(critical_missing)} critical data layer(s) missing. Score confidence moderately reduced."
        }
    else:
        return {
            "penalty_percentage": 5,
            "impact_level": "LOW",
            "explanation": "Only non-critical data layers missing. Score confidence minimally affected."
        }


def _assess_data_completeness(coverage, quality, missing):
    """Assess overall data completeness"""
    coverage = coverage or 0.0
    quality = quality or 0.0
    missing = missing or 0.0

    score = (coverage * 0.4) + (quality * 0.4) + (missing * 0.2)

    if score >= 0.8:
        return "EXCELLENT - Comprehensive data coverage"
    elif score >= 0.6:
        return "GOOD - Adequate data for analysis"
    elif score >= 0.4:
        return "MODERATE - Some data gaps noted"
    else:
        return "POOR - Significant data gaps"


def _get_data_acquisition_recommendations(missing_layers):
    """Get recommended data acquisitions based on missing layers"""
    recommendations = []

    missing_keys = {l["key"] for l in missing_layers if l["critical"]}

    if "seismic" in missing_keys:
        recommendations.append({
            "priority": "CRITICAL",
            "data": "3D Seismic Survey",
            "timeline": "3-6 months",
            "budget": "$500k-2M",
            "justification": "Essential for trap geometry validation and fault mapping"
        })

    if "wells" in missing_keys:
        recommendations.append({
            "priority": "CRITICAL",
            "data": "Slim Hole Drilling",
            "timeline": "2-4 months",
            "budget": "$100k-300k",
            "justification": "Subsurface sampling and pressure/temperature data"
        })

    if "gravity" in missing_keys or "magnetic" in missing_keys:
        recommendations.append({
            "priority": "HIGH",
            "data": "Advanced Gravity/Magnetic Inversion",
            "timeline": "1-2 months",
            "budget": "$50k-100k",
            "justification": "Refined density and susceptibility contrasts"
        })

    if "heatflow" in missing_keys:
        recommendations.append({
            "priority": "MEDIUM",
            "data": "Heat Flow Measurements",
            "timeline": "1-2 months",
            "budget": "$30k-50k",
            "justification": "Geothermal gradient assessment"
        })

    return recommendations
