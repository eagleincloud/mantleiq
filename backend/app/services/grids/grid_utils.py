"""
Shared grid utilities: color mapping, bucketing, and styling.
"""

import logging
from typing import Dict, List, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)


class ColorMapper:
    """Color mapping for prospectivity scores"""

    # Polygon grid colors (continuous gradient)
    POLYGON_COLORS = {
        "low": "#087f8c",      # Teal (0-33)
        "medium": "#d89a00",   # Orange (33-66)
        "high": "#d94848"      # Red (66-100)
    }

    # H3 grid colors (discrete quintiles)
    H3_QUINTILE_COLORS = {
        1: "#d4f1f4",  # Quintile 1 (0-20%)
        2: "#6db5c1",  # Quintile 2 (20-40%)
        3: "#2b7a8a",  # Quintile 3 (40-60%)
        4: "#1a4d59",  # Quintile 4 (60-80%)
        5: "#0a2630"   # Quintile 5 (80-100%)
    }

    @staticmethod
    def score_to_color_polygon(score: float) -> str:
        """
        Map prospectivity score [0, 1] to hex color (continuous gradient).

        Args:
            score: Score between 0 and 1

        Returns:
            Hex color string
        """
        score = max(0, min(1, score))  # Clamp to [0, 1]

        if score < 0.33:
            # Interpolate between teal and orange
            return ColorMapper._interpolate_hex(
                ColorMapper.POLYGON_COLORS["low"],
                ColorMapper.POLYGON_COLORS["medium"],
                score / 0.33
            )
        elif score < 0.66:
            # Interpolate between orange and red
            return ColorMapper._interpolate_hex(
                ColorMapper.POLYGON_COLORS["medium"],
                ColorMapper.POLYGON_COLORS["high"],
                (score - 0.33) / 0.33
            )
        else:
            # In high red zone
            return ColorMapper._interpolate_hex(
                ColorMapper.POLYGON_COLORS["medium"],
                ColorMapper.POLYGON_COLORS["high"],
                (score - 0.33) / 0.34
            )

    @staticmethod
    def score_to_quintile(score: float) -> int:
        """
        Map score [0, 1] to quintile bucket [1, 5].

        Args:
            score: Score between 0 and 1

        Returns:
            Quintile [1-5]
        """
        score = max(0, min(1, score))
        quintile = int(score * 5) + 1
        return min(quintile, 5)

    @staticmethod
    def quintile_to_color(quintile: int) -> str:
        """
        Map quintile [1-5] to hex color.

        Args:
            quintile: Bucket 1-5

        Returns:
            Hex color string
        """
        return ColorMapper.H3_QUINTILE_COLORS.get(quintile, ColorMapper.H3_QUINTILE_COLORS[3])

    @staticmethod
    def score_to_color_h3(score: float) -> str:
        """
        Map score [0, 1] to H3 quintile color.

        Args:
            score: Score between 0 and 1

        Returns:
            Hex color string
        """
        quintile = ColorMapper.score_to_quintile(score)
        return ColorMapper.quintile_to_color(quintile)

    @staticmethod
    def _interpolate_hex(color1: str, color2: str, factor: float) -> str:
        """
        Interpolate between two hex colors.

        Args:
            color1: Start hex color (e.g., '#087f8c')
            color2: End hex color
            factor: Interpolation factor [0, 1]

        Returns:
            Interpolated hex color
        """
        factor = max(0, min(1, factor))

        # Parse hex colors
        r1 = int(color1[1:3], 16)
        g1 = int(color1[3:5], 16)
        b1 = int(color1[5:7], 16)

        r2 = int(color2[1:3], 16)
        g2 = int(color2[3:5], 16)
        b2 = int(color2[5:7], 16)

        # Interpolate
        r = int(r1 + (r2 - r1) * factor)
        g = int(g1 + (g2 - g1) * factor)
        b = int(b1 + (b2 - b1) * factor)

        return f"#{r:02x}{g:02x}{b:02x}"


class ProspectStyle:
    """Styling for hydrogen prospects"""

    PROSPECT_TYPES = {
        "active_seep": {"color": "#ff6b6b", "icon": "circle-exclamation"},
        "geochemical_anomaly": {"color": "#4ecdc4", "icon": "circle-check"},
        "soil_anomaly": {"color": "#ffe66d", "icon": "circle-dot"},
        "magnetic_anomaly": {"color": "#a29bfe", "icon": "circle-plus"},
        "unknown": {"color": "#cccccc", "icon": "circle-question"}
    }

    @staticmethod
    def get_prospect_style(prospect_type: str = "unknown") -> Dict:
        """Get style for prospect type"""
        return ProspectStyle.PROSPECT_TYPES.get(prospect_type, ProspectStyle.PROSPECT_TYPES["unknown"])


class GridStyleFactory:
    """Factory for grid-type-specific styling"""

    @staticmethod
    def get_polygon_paint_spec() -> Dict:
        """Get MapLibre paint spec for polygon grid (continuous color)"""
        return {
            "fill-color": [
                "interpolate",
                ["linear"],
                ["get", "score"],
                0, "#087f8c",      # Teal (low)
                0.5, "#d89a00",    # Orange (medium)
                1, "#d94848"       # Red (high)
            ],
            "fill-opacity": 0.7,
            "fill-outline-color": "#ffffff",
            "line-width": 1
        }

    @staticmethod
    def get_h3_paint_spec() -> Dict:
        """Get MapLibre paint spec for H3 grid (discrete quintiles)"""
        return {
            "fill-color": [
                "match",
                ["get", "quintile"],
                1, "#d4f1f4",  # Quintile 1
                2, "#6db5c1",  # Quintile 2
                3, "#2b7a8a",  # Quintile 3
                4, "#1a4d59",  # Quintile 4
                5, "#0a2630",  # Quintile 5
                "#cccccc"      # Default
            ],
            "fill-opacity": 0.8,
            "fill-outline-color": "#ffffff",
            "line-width": 2
        }

    @staticmethod
    def get_prospect_paint_spec() -> Dict:
        """Get MapLibre paint spec for hydrogen prospect markers"""
        return {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 3, 12, 8],
            "circle-color": [
                "case",
                ["boolean", ["feature-state", "hover"], False],
                "#ffff00",  # Yellow on hover
                "#ff6b6b"   # Red by default
            ],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 2,
            "circle-opacity": 0.9
        }


def calculate_quintile_breaks(scores: List[float]) -> List[float]:
    """
    Calculate quintile boundaries from score distribution.

    Args:
        scores: List of scores [0, 1]

    Returns:
        List of 5 quintile boundaries
    """
    if not scores:
        return [0.2, 0.4, 0.6, 0.8, 1.0]

    sorted_scores = sorted(scores)
    breaks = []
    for percentile in [20, 40, 60, 80, 100]:
        idx = int(len(sorted_scores) * percentile / 100)
        idx = min(idx, len(sorted_scores) - 1)
        breaks.append(sorted_scores[idx])

    return breaks


def score_statistics(scores: Dict[str, float]) -> Dict:
    """
    Calculate statistics on score distribution.

    Args:
        scores: Dict of cell_id -> score

    Returns:
        Dict with min, max, mean, median, stdev
    """
    score_list = list(scores.values())

    if not score_list:
        return {
            "min": 0,
            "max": 0,
            "mean": 0,
            "median": 0,
            "stdev": 0,
            "count": 0
        }

    arr = np.array(score_list)
    return {
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "stdev": float(np.std(arr)),
        "count": len(score_list)
    }
