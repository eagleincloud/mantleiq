"""
Gravity feature extraction from raster data.
Computes 5 gravity-derived features for prospectivity scoring:
1. gravity_anomaly_score - normalized Bouguer anomaly
2. gravity_gradient_score - strength of gravity gradient (basement edges)
3. gravity_edge_density - count of high-gradient pixels per km²
4. gravity_magnetic_overlap_score - joint gravity-magnetic signal
5. basin_proxy_score - inverted gravity for sediment thickness
"""

from typing import Optional, Tuple
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Gravity anomaly normalization ranges (typical for Bouguer anomaly in mGal)
GRAVITY_MIN_MGAL = -50.0
GRAVITY_MAX_MGAL = 100.0

# Gradient threshold for edge detection (mGal/km)
GRADIENT_THRESHOLD_DEFAULT = 5.0  # mGal/km


def gravity_anomaly_score(
    bouguer_anomaly_mgal: float,
    min_val: float = GRAVITY_MIN_MGAL,
    max_val: float = GRAVITY_MAX_MGAL
) -> float:
    """
    Normalize Bouguer gravity anomaly to [0, 100] score.

    Args:
        bouguer_anomaly_mgal: Bouguer anomaly value in mGal
        min_val: Minimum expected value (default -50 mGal)
        max_val: Maximum expected value (default +100 mGal)

    Returns:
        Normalized score [0, 100]
    """
    if np.isnan(bouguer_anomaly_mgal) or bouguer_anomaly_mgal is None:
        return 50.0  # Neutral score for missing data

    # Clamp to range
    value = max(min_val, min(max_val, bouguer_anomaly_mgal))

    # Linear normalization to [0, 1]
    normalized = (value - min_val) / (max_val - min_val)

    # Scale to [0, 100]
    return max(0.0, min(100.0, normalized * 100.0))


def gravity_gradient_score(
    gradient_mgal_per_km: float,
    threshold: float = GRADIENT_THRESHOLD_DEFAULT,
    max_gradient: float = 50.0
) -> float:
    """
    Score based on gravity gradient strength (basement/fault edges).

    High gradient indicates sharp structural features (basement steps, fault zones).

    Args:
        gradient_mgal_per_km: Computed gradient in mGal/km
        threshold: Threshold for significant gradient (default 5 mGal/km)
        max_gradient: Maximum expected gradient (default 50 mGal/km)

    Returns:
        Normalized score [0, 100]
    """
    if np.isnan(gradient_mgal_per_km) or gradient_mgal_per_km is None:
        return 0.0

    # Absolute value of gradient
    grad_abs = abs(gradient_mgal_per_km)

    # Below threshold = low score
    if grad_abs < threshold:
        return 0.0

    # Normalize above threshold
    normalized = (grad_abs - threshold) / (max_gradient - threshold)
    normalized = max(0.0, min(1.0, normalized))

    return normalized * 100.0


def gravity_edge_density(
    high_gradient_pixels: int,
    cell_area_km2: float = 100.0,
    expected_density_per_km2: float = 0.5
) -> float:
    """
    Score based on count of high-gradient pixels per unit area.

    High density indicates complex basement structure with many faults/boundaries.

    Args:
        high_gradient_pixels: Number of pixels with high gradient in cell
        cell_area_km2: Area of grid cell in km²
        expected_density_per_km2: Expected density for normalization (default 0.5/km²)

    Returns:
        Normalized score [0, 100]
    """
    if high_gradient_pixels == 0 or cell_area_km2 == 0:
        return 0.0

    # Density: pixels per km²
    density = high_gradient_pixels / cell_area_km2

    # Normalize to [0, 100]
    normalized = min(1.0, density / expected_density_per_km2)

    return normalized * 100.0


def gravity_magnetic_overlap_score(
    gravity_score: float,
    magnetic_score: float
) -> float:
    """
    Joint gravity-magnetic signal (mafic/ultramafic basement indicator).

    High overlap in both gravity and magnetic anomalies indicates strong
    basement signal, likely mafic/ultramafic composition (good for H2 generation).

    Args:
        gravity_score: Gravity anomaly score [0, 100]
        magnetic_score: Magnetic anomaly score [0, 100]

    Returns:
        Overlap score [0, 100]
    """
    if gravity_score is None or magnetic_score is None:
        return 0.0

    # Geometric mean of both scores (emphasizes high values in both)
    overlap = (gravity_score * magnetic_score) / 100.0

    return max(0.0, min(100.0, overlap))


def basin_proxy_score(
    gravity_anomaly_score_val: float
) -> float:
    """
    Inverted gravity score as proxy for sediment thickness.

    Low gravity anomalies indicate thick sedimentary cover (thick basin).
    This inverts the gravity_anomaly_score to use as trap/seal proxy.

    Args:
        gravity_anomaly_score_val: Gravity anomaly score [0, 100]

    Returns:
        Basin thickness proxy [0, 100]
    """
    if gravity_anomaly_score_val is None:
        return 50.0

    # Invert: low gravity (low score) → high basin proxy (high score)
    return max(0.0, min(100.0, 100.0 - gravity_anomaly_score_val))


def compute_gravity_gradient(
    raster_data: np.ndarray,
    resolution_km: float = 0.05
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute gradient from raster data using Sobel operator.

    Args:
        raster_data: 2D numpy array of gravity anomaly values
        resolution_km: Grid resolution in km

    Returns:
        (gradient_magnitude, gradient_direction) arrays
    """
    try:
        from scipy import ndimage

        # Sobel operators for gradient computation
        sx = ndimage.sobel(raster_data, axis=0)
        sy = ndimage.sobel(raster_data, axis=1)

        # Magnitude and direction
        magnitude = np.sqrt(sx**2 + sy**2) / resolution_km

        # Direction (atan2 of gradients)
        direction = np.arctan2(sy, sx)

        return magnitude, direction

    except ImportError:
        logger.warning("scipy not available for gradient computation - using finite difference")
        # Fallback: finite difference
        magnitude = np.zeros_like(raster_data, dtype=float)
        magnitude[1:-1, 1:-1] = np.sqrt(
            (raster_data[2:, 1:-1] - raster_data[:-2, 1:-1])**2 +
            (raster_data[1:-1, 2:] - raster_data[1:-1, :-2])**2
        ) / (2 * resolution_km)
        return magnitude, None


def extract_cell_gravity_features(
    raster_array: np.ndarray,
    cell_centroid_idx: Tuple[int, int],
    window_size: int = 5,
    magnetic_score: Optional[float] = None
) -> dict:
    """
    Extract all gravity-derived features for a single grid cell.

    Args:
        raster_array: 2D numpy array of gravity anomaly (mGal)
        cell_centroid_idx: (row, col) indices of cell centroid in raster
        window_size: Window around centroid for gradient computation
        magnetic_score: Optional magnetic anomaly score for overlap calculation

    Returns:
        Dictionary with all gravity feature scores
    """
    row, col = cell_centroid_idx
    h, w = raster_array.shape

    # Ensure indices are valid
    if row < 0 or row >= h or col < 0 or col >= w:
        return {
            'gravity_anomaly_score': 50.0,
            'gravity_gradient_score': 0.0,
            'gravity_edge_density': 0.0,
            'gravity_magnetic_overlap_score': 0.0,
            'basin_proxy_score': 50.0,
        }

    # Feature 1: Anomaly score at centroid
    anomaly_val = raster_array[row, col]
    feat1 = gravity_anomaly_score(anomaly_val)

    # Feature 5: Basin proxy (easy - just invert anomaly)
    feat5 = basin_proxy_score(feat1)

    # Extract window for gradient computation
    r_start = max(0, row - window_size // 2)
    r_end = min(h, row + window_size // 2 + 1)
    c_start = max(0, col - window_size // 2)
    c_end = min(w, col + window_size // 2 + 1)

    window = raster_array[r_start:r_end, c_start:c_end]

    if window.size == 0:
        gradient = 0.0
        edge_density = 0.0
    else:
        # Feature 2 & 3: Gradient and edge density
        gradient_mag, _ = compute_gravity_gradient(window, resolution_km=0.05)
        gradient = float(np.nanmean(gradient_mag))
        feat2 = gravity_gradient_score(gradient)

        # Edge density: count pixels with high gradient
        high_grad_count = np.sum(gradient_mag > GRADIENT_THRESHOLD_DEFAULT)
        window_area_km2 = (window.shape[0] * window.shape[1]) * (0.05**2)
        feat3 = gravity_edge_density(high_grad_count, cell_area_km2=window_area_km2)

    # Feature 4: Magnetic overlap (if magnetic score provided)
    if magnetic_score is not None and magnetic_score > 0:
        feat4 = gravity_magnetic_overlap_score(feat1, magnetic_score)
    else:
        feat4 = 0.0

    return {
        'gravity_anomaly_score': feat1,
        'gravity_gradient_score': feat2,
        'gravity_edge_density': feat3,
        'gravity_magnetic_overlap_score': feat4,
        'basin_proxy_score': feat5,
    }


def extract_gravity_features_from_file(
    gravity_file_path: str,
    grid_cells_with_coords: list,
    magnetic_scores: Optional[dict] = None
) -> dict:
    """
    Extract gravity features from GeoTIFF file for multiple grid cells.

    Args:
        gravity_file_path: Path to gravity GeoTIFF (COG format)
        grid_cells_with_coords: List of (cell_id, lat, lon) tuples
        magnetic_scores: Optional dict {cell_id: magnetic_score}

    Returns:
        Dictionary {cell_id: feature_dict}
    """
    try:
        import rasterio
        from rasterio.windows import Window
    except ImportError:
        logger.error("rasterio not available - cannot load gravity raster")
        # Return default scores
        return {
            cell_id: {
                'gravity_anomaly_score': 50.0,
                'gravity_gradient_score': 0.0,
                'gravity_edge_density': 0.0,
                'gravity_magnetic_overlap_score': 0.0,
                'basin_proxy_score': 50.0,
            }
            for cell_id, _, _ in grid_cells_with_coords
        }

    results = {}

    try:
        with rasterio.open(gravity_file_path) as src:
            # Read full raster (assuming file is manageable size)
            raster_array = src.read(1)  # Band 1

            for cell_id, lat, lon in grid_cells_with_coords:
                try:
                    # Get raster indices from lat/lon
                    # Note: rasterio returns (row, col) from xy
                    row, col = src.index(lon, lat)
                    row, col = int(row), int(col)

                    # Get magnetic score if available
                    mag_score = None
                    if magnetic_scores and cell_id in magnetic_scores:
                        mag_score = magnetic_scores[cell_id]

                    # Extract features
                    features = extract_cell_gravity_features(
                        raster_array,
                        (row, col),
                        magnetic_score=mag_score
                    )
                    results[cell_id] = features

                except Exception as e:
                    logger.warning(f"Error extracting features for cell {cell_id}: {e}")
                    results[cell_id] = {
                        'gravity_anomaly_score': 50.0,
                        'gravity_gradient_score': 0.0,
                        'gravity_edge_density': 0.0,
                        'gravity_magnetic_overlap_score': 0.0,
                        'basin_proxy_score': 50.0,
                    }

    except Exception as e:
        logger.error(f"Error reading gravity raster: {e}")
        # Return default scores for all cells
        return {
            cell_id: {
                'gravity_anomaly_score': 50.0,
                'gravity_gradient_score': 0.0,
                'gravity_edge_density': 0.0,
                'gravity_magnetic_overlap_score': 0.0,
                'basin_proxy_score': 50.0,
            }
            for cell_id, _, _ in grid_cells_with_coords
        }

    return results
