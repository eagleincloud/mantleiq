"""
Feature normalization utilities for prospectivity scoring.
"""

import math
from typing import Optional


def clamp01(value: float) -> float:
    """Clamp a value to [0, 1] range."""
    return max(0.0, min(1.0, value))


def linear_normalize(value: float, min_val: float, max_val: float) -> float:
    """Linearly normalize a value to [0, 1] given min and max bounds."""
    if min_val >= max_val:
        return 0.5
    normalized = (value - min_val) / (max_val - min_val)
    return clamp01(normalized)


def inverse_distance_weight(distance_km: float, max_distance_km: float) -> float:
    """
    Compute inverse distance weight: proximity score decreases with distance.
    Returns 1.0 at distance=0, approaches 0 as distance approaches max_distance_km.
    """
    if distance_km <= 0:
        return 1.0
    if distance_km >= max_distance_km:
        return 0.0
    return clamp01(1.0 - (distance_km / max_distance_km))


def sigmoid_normalize(value: float, midpoint: float = 0.5, steepness: float = 10.0) -> float:
    """
    Sigmoid normalization: S-curve from 0 to 1 centered at midpoint.
    Useful for smooth transitions (e.g., thermodynamic favorability).
    """
    try:
        exponent = -steepness * (value - midpoint)
        return 1.0 / (1.0 + math.exp(exponent))
    except (ValueError, OverflowError):
        return 0.5


def percentile_rank(value: float, percentile_p50: float, percentile_p95: float) -> float:
    """
    Rank a value based on percentile thresholds.
    p50 = 50th percentile, p95 = 95th percentile.
    Returns 0.5 at p50, 1.0 at p95, scales linearly between.
    """
    if value <= percentile_p50:
        return clamp01(0.5 * (value / percentile_p50))
    elif value <= percentile_p95:
        return clamp01(0.5 + 0.5 * ((value - percentile_p50) / (percentile_p95 - percentile_p50)))
    else:
        return 1.0


def log_normalize(value: float, base: float = 10.0) -> float:
    """Logarithmic normalization for skewed distributions (e.g., fault density)."""
    if value <= 0:
        return 0.0
    return clamp01(math.log(value + 1, base) / math.log(100, base))


def handle_missing_data(
    value: Optional[float],
    default_score: float = 0.5,
    penalty_factor: float = 0.1
) -> tuple[float, bool]:
    """
    Handle missing data gracefully.

    Returns:
        (normalized_score, is_missing)
        - If value is None/NaN: returns (default_score, True)
        - Otherwise: returns (value clamped to [0,1], False)
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return (default_score, True)
    return (clamp01(value), False)
