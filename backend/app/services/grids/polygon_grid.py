"""
Polygon-based grid service.
Manages rectangular grid cells for spatial analysis.
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class PolygonGridParams:
    """Polygon grid configuration"""
    origin_lon: float = -98.0
    origin_lat: float = 37.0
    cell_size_km: float = 100.0  # Approximate size in km
    rows: int = 10
    cols: int = 10
    projection: str = "epsg:4326"


class PolygonGridService:
    """Service for rectangular/square polygon grid operations"""

    @staticmethod
    def generate_polygon_grid(origin_lon: float,
                              origin_lat: float,
                              cell_size_degrees: float,
                              rows: int = 10,
                              cols: int = 10) -> List[Dict]:
        """
        Generate polygon grid cells.

        Args:
            origin_lon: Western boundary (longitude)
            origin_lat: Southern boundary (latitude)
            cell_size_degrees: Cell size in degrees (roughly 1° ≈ 111 km)
            rows: Number of rows
            cols: Number of columns

        Returns:
            List of cell dicts with geometry and indices
        """
        cells = []

        for row in range(rows):
            for col in range(cols):
                lon_min = origin_lon + (col * cell_size_degrees)
                lon_max = lon_min + cell_size_degrees
                lat_min = origin_lat + (row * cell_size_degrees)
                lat_max = lat_min + cell_size_degrees

                cell = {
                    "grid_x": col,
                    "grid_y": row,
                    "centroid_lon": (lon_min + lon_max) / 2,
                    "centroid_lat": (lat_min + lat_max) / 2,
                    "bounds": {
                        "west": lon_min,
                        "east": lon_max,
                        "south": lat_min,
                        "north": lat_max
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [lon_min, lat_min],
                            [lon_max, lat_min],
                            [lon_max, lat_max],
                            [lon_min, lat_max],
                            [lon_min, lat_min]
                        ]]
                    }
                }
                cells.append(cell)

        logger.info(f"Generated {len(cells)} polygon grid cells ({rows}x{cols})")
        return cells

    @staticmethod
    def polygon_to_geojson_feature(cell_data: Dict, properties: Dict = None) -> Dict:
        """
        Convert polygon cell to GeoJSON feature.

        Args:
            cell_data: Cell dict with geometry
            properties: Optional additional properties

        Returns:
            GeoJSON Feature dict
        """
        feature = {
            "type": "Feature",
            "id": f"polygon_{cell_data['grid_x']}_{cell_data['grid_y']}",
            "properties": {
                "grid_x": cell_data['grid_x'],
                "grid_y": cell_data['grid_y'],
                "centroid_lon": cell_data['centroid_lon'],
                "centroid_lat": cell_data['centroid_lat'],
                **(properties or {})
            },
            "geometry": cell_data['geometry']
        }
        return feature

    @staticmethod
    def get_cell_at_point(latitude: float,
                          longitude: float,
                          origin_lon: float,
                          origin_lat: float,
                          cell_size_degrees: float) -> Tuple[int, int]:
        """
        Determine which grid cell contains a point.

        Args:
            latitude: Point latitude
            longitude: Point longitude
            origin_lon: Grid origin longitude
            origin_lat: Grid origin latitude
            cell_size_degrees: Cell size in degrees

        Returns:
            (grid_x, grid_y) tuple or None if outside grid
        """
        if cell_size_degrees <= 0:
            return None

        grid_x = int((longitude - origin_lon) / cell_size_degrees)
        grid_y = int((latitude - origin_lat) / cell_size_degrees)

        return (grid_x, grid_y)

    @staticmethod
    def get_neighbors(grid_x: int, grid_y: int, distance: int = 1) -> List[Tuple[int, int]]:
        """
        Get neighboring cells in grid.

        Args:
            grid_x: Cell X coordinate
            grid_y: Cell Y coordinate
            distance: Ring distance (1 = direct neighbors)

        Returns:
            List of (grid_x, grid_y) tuples
        """
        neighbors = []
        for dx in range(-distance, distance + 1):
            for dy in range(-distance, distance + 1):
                if dx == 0 and dy == 0:
                    continue
                if max(abs(dx), abs(dy)) <= distance:
                    neighbors.append((grid_x + dx, grid_y + dy))
        return neighbors

    @staticmethod
    def cell_area_km2(cell_size_degrees: float, latitude: float = 0) -> float:
        """
        Estimate cell area in km² (accounting for latitude).

        Args:
            cell_size_degrees: Cell size in degrees
            latitude: Latitude for adjustment (default equator)

        Returns:
            Approximate area in km²
        """
        import math
        # 1 degree ≈ 111 km
        km_per_degree_lon = 111 * math.cos(math.radians(latitude))
        km_per_degree_lat = 111
        return cell_size_degrees * km_per_degree_lon * cell_size_degrees * km_per_degree_lat


def generate_polygon_prospectivity_geojson(polygon_cells: List[Dict],
                                           scores: Dict[str, float]) -> Dict:
    """
    Generate GeoJSON for polygon grid with prospectivity scores (continuous gradient).

    Args:
        polygon_cells: List of polygon cell dicts
        scores: Dict mapping cell_id to prospectivity score [0, 1]

    Returns:
        GeoJSON FeatureCollection
    """
    features = []

    for cell in polygon_cells:
        cell_key = f"polygon_{cell['grid_x']}_{cell['grid_y']}"
        score = scores.get(cell_key, 0.5)

        # Normalize score to 0-100
        score_100 = score * 100

        feature = PolygonGridService.polygon_to_geojson_feature(cell, {
            "score": score,
            "score_100": score_100
        })

        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }
