"""
Data completeness scoring: calculate confidence from actual available data layers.
Replaces random test values with real layer coverage metrics.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Required data layers for MVP (expand as needed)
REQUIRED_LAYERS = [
    "geology_macrostrat",      # Lithology/geologic units
    "faults_usgs",             # Fault traces
    "gravity_noaa",            # Gravity anomaly (Bouguer)
    "magnetic_emag2",          # Magnetic anomaly
    "heat_flow_ihfc",          # Heat flow measurements
    "dem_srtm",                # Digital elevation model (optional)
    "seismic_data",            # Seismic velocity/interpretation (optional)
    "caprock_data",            # Caprock thickness (optional)
]

# Weights for missing layer impact (sum should = 1.0)
LAYER_WEIGHTS = {
    "geology_macrostrat": 0.15,   # Critical for lithology
    "faults_usgs": 0.20,           # Critical for pathways
    "gravity_noaa": 0.20,          # Critical for structure
    "magnetic_emag2": 0.15,        # Important for composition
    "heat_flow_ihfc": 0.15,        # Important for generation
    "dem_srtm": 0.05,              # Nice to have
    "seismic_data": 0.05,          # Nice to have
    "caprock_data": 0.05,          # Nice to have
}


@dataclass
class DataCompletenessResult:
    """Result of data completeness calculation."""
    data_coverage: float           # Fraction available: [0, 1]
    data_quality: float            # Average quality of available layers: [0, 1]
    missing_completeness: float    # 1 - (weighted missing): [0, 1]

    available_count: int           # Number of available layers
    required_count: int            # Total required layers
    available_layers: List[str]    # Names of available layers
    missing_layers: List[str]      # Names of missing layers
    layer_qualities: dict          # {layer_name: quality_score}

    recency_score: float           # Data freshness: [0, 1]
    confidence_raw: float          # Result of formula: 0.4*coverage + 0.4*quality + 0.2*completeness


def calculate_data_completeness(
    basin_id: str,
    session=None,
    layers_status: Optional[dict] = None
) -> DataCompletenessResult:
    """
    Calculate data completeness for a basin.

    Args:
        basin_id: UUID of the basin
        session: SQLAlchemy session (for database query)
        layers_status: Optional dict of layer availability for testing {layer_name: available}

    Returns:
        DataCompletenessResult with completeness metrics
    """

    # If layers_status provided (for testing), use it directly
    if layers_status is not None:
        return _calculate_from_dict(layers_status)

    # Otherwise, query database
    if session is None:
        logger.warning("No session provided and no layers_status dict - returning minimal completeness")
        return _default_completeness()

    try:
        from ..models.orm import DataLayersORM
        from sqlalchemy import func

        # Query available layers for this basin
        query = session.query(
            DataLayersORM.name,
            DataLayersORM.data_quality,
            DataLayersORM.source_confidence,
            DataLayersORM.acquisition_date
        ).filter(DataLayersORM.basin_id == basin_id)

        results = query.all()
        available_dict = {row[0]: {
            'quality': row[1] or 0.8,
            'confidence': row[2] or 0.8,
            'date': row[3]
        } for row in results}

        return _calculate_from_dict(available_dict)

    except Exception as e:
        logger.error(f"Error calculating data completeness: {e}")
        return _default_completeness()


def _calculate_from_dict(layers_dict: dict) -> DataCompletenessResult:
    """
    Calculate completeness from a dictionary of available layers.

    Args:
        layers_dict: {layer_name: availability_info or True/False}

    Returns:
        DataCompletenessResult
    """
    available_layers = []
    missing_layers = []
    layer_qualities = {}
    quality_sum = 0.0
    quality_count = 0

    # Determine what's available
    for layer_name in REQUIRED_LAYERS:
        if layer_name in layers_dict:
            layer_info = layers_dict[layer_name]

            # Extract quality (handle both dict and boolean inputs)
            if isinstance(layer_info, dict):
                quality = layer_info.get('quality', 0.8)
            elif isinstance(layer_info, (int, float)):
                quality = float(layer_info)
            elif isinstance(layer_info, bool):
                quality = 0.9 if layer_info else 0.0
            else:
                quality = 0.8  # Default

            available_layers.append(layer_name)
            layer_qualities[layer_name] = quality
            quality_sum += quality
            quality_count += 1
        else:
            missing_layers.append(layer_name)

    # Calculate metrics
    available_count = len(available_layers)
    required_count = len(REQUIRED_LAYERS)

    # data_coverage: fraction of required layers available
    data_coverage = available_count / required_count if required_count > 0 else 0.0

    # data_quality: average quality of available layers
    data_quality = (quality_sum / quality_count) if quality_count > 0 else 0.0

    # missing_completeness: 1 - weighted missingness
    missing_weight = sum(LAYER_WEIGHTS.get(layer, 0.0) for layer in missing_layers)
    missing_completeness = 1.0 - missing_weight

    # recency_score (placeholder - would check acquisition dates in real implementation)
    recency_score = _calculate_recency(layers_dict)

    # confidence_raw: formula from ensemble.py
    confidence_raw = (
        0.40 * data_coverage +
        0.40 * data_quality +
        0.20 * missing_completeness
    )

    return DataCompletenessResult(
        data_coverage=max(0.0, min(1.0, data_coverage)),
        data_quality=max(0.0, min(1.0, data_quality)),
        missing_completeness=max(0.0, min(1.0, missing_completeness)),
        available_count=available_count,
        required_count=required_count,
        available_layers=available_layers,
        missing_layers=missing_layers,
        layer_qualities=layer_qualities,
        recency_score=recency_score,
        confidence_raw=max(0.0, min(1.0, confidence_raw))
    )


def _calculate_recency(layers_dict: dict) -> float:
    """Calculate data freshness score based on acquisition dates."""
    if not layers_dict:
        return 0.5

    dates = []
    for layer_info in layers_dict.values():
        if isinstance(layer_info, dict) and 'date' in layer_info:
            date = layer_info['date']
            if isinstance(date, datetime):
                dates.append(date)

    if not dates:
        return 0.8  # Default if no dates available

    # Average age of data
    avg_date = sum(dates, timedelta()) / len(dates)
    age_days = (datetime.utcnow() - avg_date).days

    # Score: 1.0 if <1 year old, declining to 0.5 at 5 years
    if age_days < 365:
        return 1.0
    elif age_days < 1825:  # 5 years
        return 1.0 - (age_days - 365) / 1460  # Linear decay
    else:
        return 0.5

    return 0.5


def _default_completeness() -> DataCompletenessResult:
    """Return conservative completeness estimate (50% coverage)."""
    return DataCompletenessResult(
        data_coverage=0.5,
        data_quality=0.7,
        missing_completeness=0.5,
        available_count=0,
        required_count=len(REQUIRED_LAYERS),
        available_layers=[],
        missing_layers=REQUIRED_LAYERS.copy(),
        layer_qualities={},
        recency_score=0.5,
        confidence_raw=0.5
    )


def format_completeness_summary(result: DataCompletenessResult) -> str:
    """Format completeness result as human-readable summary."""
    return f"""
Data Completeness Summary:
- Available: {result.available_count}/{result.required_count} layers ({result.data_coverage*100:.1f}%)
- Data Quality: {result.data_quality*100:.1f}%
- Missing Completeness: {result.missing_completeness*100:.1f}%
- Recency Score: {result.recency_score*100:.1f}%
- Overall Confidence (raw): {result.confidence_raw*100:.1f}%

Available Layers: {', '.join(result.available_layers) if result.available_layers else 'None'}
Missing Layers: {', '.join(result.missing_layers) if result.missing_layers else 'None'}
    """.strip()
