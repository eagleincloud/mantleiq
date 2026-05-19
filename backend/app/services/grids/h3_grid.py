"""
H3 Hierarchical Spatial Index grid service.
Generates and manages hexagonal grid cells for spatial analysis.
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import h3
    H3_AVAILABLE = True
except ImportError:
    H3_AVAILABLE = False
    logger.warning("h3-py not installed. H3 grid functionality disabled.")


@dataclass
class H3GridParams:
    """H3 grid configuration"""
    resolution: int = 5  # 0-15, lower = larger cells
    basin_bounds: Tuple[float, float, float, float] = (-98.0, 37.0, -93.0, 40.0)  # (west, south, east, north)


class H3GridService:
    """Service for H3 hexagonal grid operations"""

    @staticmethod
    def generate_h3_grid(basin_bounds: Tuple[float, float, float, float],
                         resolution: int = 5) -> List[str]:
        """
        Generate H3 cells covering a basin.

        Args:
            basin_bounds: (west, south, east, north) in degrees
            resolution: H3 resolution level (0-15)

        Returns:
            List of H3 IDs covering the basin
        """
        if not H3_AVAILABLE:
            logger.error("h3-py not available")
            return []

        west, south, east, north = basin_bounds
        h3_ids = []

        try:
            # Generate polygon covering the basin bounds
            # Create as list of (lat, lon) tuples for LatLngPoly
            polygon_coords = [(south, west), (south, east), (north, east), (north, west)]
            polygon = h3.LatLngPoly(polygon_coords)

            # Use polygon_to_cells to get all H3 cells covering the polygon
            h3_ids = h3.polygon_to_cells(polygon, resolution)

            logger.info(f"Generated {len(h3_ids)} H3 cells at resolution {resolution}")
            return h3_ids

        except Exception as e:
            logger.error(f"Error generating H3 grid: {e}")
            return []

    @staticmethod
    def h3_to_geojson_feature(h3_id: str, properties: Dict = None) -> Dict:
        """
        Convert H3 ID to GeoJSON feature.

        Args:
            h3_id: H3 cell identifier
            properties: Optional feature properties

        Returns:
            GeoJSON Feature dict
        """
        if not H3_AVAILABLE:
            return {}

        try:
            # Get cell boundary
            boundary = h3.cell_to_boundary(h3_id)
            # Boundary is list of (lat, lon), convert to (lon, lat) for GeoJSON
            coordinates = [[[lon, lat] for lat, lon in boundary]]
            coordinates[0].append(coordinates[0][0])  # Close ring

            feature = {
                "type": "Feature",
                "id": h3_id,
                "properties": properties or {"h3_id": h3_id},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coordinates
                }
            }
            return feature

        except Exception as e:
            logger.error(f"Error converting H3 to GeoJSON: {e}")
            return {}

    @staticmethod
    def get_h3_centroid(h3_id: str) -> Tuple[float, float]:
        """
        Get centroid of H3 cell.

        Args:
            h3_id: H3 cell identifier

        Returns:
            (latitude, longitude) tuple
        """
        if not H3_AVAILABLE:
            return (0, 0)

        try:
            lat, lon = h3.cell_to_latlng(h3_id)
            return (lat, lon)
        except Exception as e:
            logger.error(f"Error getting H3 centroid: {e}")
            return (0, 0)

    @staticmethod
    def get_h3_neighbors(h3_id: str, distance: int = 1) -> List[str]:
        """
        Get neighboring H3 cells.

        Args:
            h3_id: H3 cell identifier
            distance: Ring distance (1 = direct neighbors)

        Returns:
            List of neighboring H3 IDs
        """
        if not H3_AVAILABLE:
            return []

        try:
            # Get all cells within distance (disk includes center cell)
            neighbors = h3.grid_disk(h3_id, distance)
            # Remove the center cell itself
            neighbors.discard(h3_id)
            return list(neighbors)
        except Exception as e:
            logger.error(f"Error getting H3 neighbors: {e}")
            return []

    @staticmethod
    def h3_cell_area_km2(h3_id: str) -> float:
        """
        Get approximate area of H3 cell in km².

        Args:
            h3_id: H3 cell identifier

        Returns:
            Area in km²
        """
        if not H3_AVAILABLE:
            return 0.0

        try:
            # Default unit is km^2
            area_km2 = h3.cell_area(h3_id)
            return area_km2
        except Exception as e:
            logger.error(f"Error getting H3 cell area: {e}")
            return 0.0

    @staticmethod
    def point_to_h3(latitude: float, longitude: float, resolution: int = 5) -> str:
        """
        Convert lat/lon to H3 cell ID.

        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            resolution: H3 resolution level

        Returns:
            H3 cell ID
        """
        if not H3_AVAILABLE:
            return ""

        try:
            return h3.latlng_to_cell(latitude, longitude, resolution)
        except Exception as e:
            logger.error(f"Error converting point to H3: {e}")
            return ""


def generate_h3_prospectivity_geojson(h3_cells: List[Dict],
                                      scores: Dict[str, float],
                                      quintile_breaks: List[float] = None) -> Dict:
    """
    Generate GeoJSON for H3 grid with prospectivity scores (discretized by quintile).

    Args:
        h3_cells: List of H3 cell dicts from database
        scores: Dict mapping h3_id to prospectivity score [0, 1]
        quintile_breaks: Optional custom quintile boundaries

    Returns:
        GeoJSON FeatureCollection
    """
    if not quintile_breaks:
        # Default quintile breaks: 0.2, 0.4, 0.6, 0.8, 1.0
        quintile_breaks = [0.2, 0.4, 0.6, 0.8, 1.0]

    features = []
    for cell in h3_cells:
        h3_id = cell['h3_id']
        score = scores.get(h3_id, 0.5)

        # Determine quintile bucket (1-5)
        quintile = 1
        for i, break_val in enumerate(quintile_breaks):
            if score > break_val:
                quintile = i + 2
        quintile = min(quintile, 5)  # Cap at 5

        # Create feature
        feature = H3GridService.h3_to_geojson_feature(h3_id, {
            "h3_id": h3_id,
            "score": score,
            "quintile": quintile,
            "bucket": quintile
        })

        if feature:
            features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }
