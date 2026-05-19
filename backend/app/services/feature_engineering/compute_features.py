"""
Feature engineering service: compute 25+ geospatial features for grid cells.
Spatial joins, raster sampling, interpolation, and metric calculations.
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)


@dataclass
class GridCellFeatures:
    """Computed features for a single grid cell."""
    cell_id: str
    basin_id: str

    # Structural features
    fault_density: float = 0.0
    fault_intersection_count: int = 0
    structural_complexity: float = 0.0

    # Proximity features
    ultramafic_proximity_km: float = 100.0
    seep_proximity_km: float = 100.0
    fold_proximity_km: float = 100.0

    # Anomaly features
    gravity_anomaly: float = 0.0
    gravity_gradient: float = 0.0
    magnetic_anomaly: float = 0.0
    magnetic_gradient: float = 0.0

    # Thermal features
    heat_flow_indicator: float = 0.0
    heat_flow_value: float = 0.0
    geothermal_gradient: float = 0.0

    # Lithology features
    ultramafic_coverage: float = 0.0
    mafic_coverage: float = 0.0
    sedimentary_coverage: float = 0.0

    # Topography features
    elevation_mean: float = 0.0
    relief: float = 0.0
    slope: float = 0.0

    # Composite scores (normalized 0-1)
    f_generation: float = 0.0
    f_fluid_interaction: float = 0.0
    f_structural_pathways: float = 0.0
    f_trap_retention: float = 0.0
    f_surface_indicators: float = 0.0
    f_thermodynamic: float = 0.0


class FeatureComputer:
    """
    Compute all 25+ geospatial features for a grid cell.

    Features are normalized to [0, 1] where applicable.
    """

    def __init__(self):
        """Initialize feature computer with default parameters."""
        self.fault_density_threshold = 5  # km
        self.ultramafic_max_distance = 100  # km
        self.seep_max_distance = 100  # km
        self.gravity_anomaly_threshold = 50  # mGal

    def compute_cell_features(
        self,
        cell_id: str,
        basin_id: str,
        # Structural data
        fault_count: int = 0,
        fault_intersections: int = 0,
        fold_count: int = 0,
        # Proximity data
        nearest_fault_km: float = 100.0,
        nearest_ultramafic_km: float = 100.0,
        nearest_seep_km: float = 100.0,
        # Anomaly data
        gravity_value: float = 0.0,
        gravity_std: float = 10.0,
        magnetic_value: float = 0.0,
        magnetic_std: float = 200.0,
        # Thermal data
        heat_flow_mwm2: float = 60.0,
        geothermal_gradient: float = 25.0,
        # Lithology coverage (%)
        ultramafic_pct: float = 0.0,
        mafic_pct: float = 0.0,
        sedimentary_pct: float = 80.0,
        # Topography
        elevation_m: float = 0.0,
        relief_m: float = 0.0,
        slope_deg: float = 0.0,
    ) -> GridCellFeatures:
        """
        Compute all features for a grid cell.

        Args:
            cell_id: Grid cell UUID
            basin_id: Basin UUID
            fault_count: Number of faults in/near cell
            fault_intersections: Number of fault intersections
            fold_count: Number of folds in/near cell
            nearest_fault_km: Distance to nearest fault (km)
            nearest_ultramafic_km: Distance to nearest ultramafic rock (km)
            nearest_seep_km: Distance to nearest known seep (km)
            gravity_value: Bouguer gravity anomaly (mGal)
            gravity_std: Standard deviation of gravity in region
            magnetic_value: Magnetic anomaly (nT)
            magnetic_std: Standard deviation of magnetic in region
            heat_flow_mwm2: Heat flow value (mW/m²)
            geothermal_gradient: Geothermal gradient (°C/km)
            ultramafic_pct: Ultramafic rock coverage (%)
            mafic_pct: Mafic rock coverage (%)
            sedimentary_pct: Sedimentary coverage (%)
            elevation_m: Mean elevation (m)
            relief_m: Topographic relief (m)
            slope_deg: Mean slope (degrees)

        Returns:
            GridCellFeatures with all 25+ computed features
        """
        features = GridCellFeatures(cell_id=cell_id, basin_id=basin_id)

        # Compute structural features
        features.fault_intersection_count = fault_intersections
        features.fault_density = self._normalize_fault_density(fault_count)
        features.structural_complexity = self._compute_structural_complexity(
            fault_count, fold_count, fault_intersections
        )

        # Compute proximity features (inverse distance weighted)
        features.ultramafic_proximity_km = nearest_ultramafic_km
        features.seep_proximity_km = nearest_seep_km
        features.fold_proximity_km = nearest_fault_km

        # Compute anomaly features (normalized by std dev)
        features.gravity_anomaly = self._normalize_anomaly(gravity_value, gravity_std)
        features.gravity_gradient = self._compute_gravity_gradient(gravity_value)
        features.magnetic_anomaly = self._normalize_anomaly(magnetic_value, magnetic_std)
        features.magnetic_gradient = self._compute_magnetic_gradient(magnetic_value)

        # Compute thermal features
        features.heat_flow_value = heat_flow_mwm2
        features.geothermal_gradient = geothermal_gradient
        features.heat_flow_indicator = self._normalize_heat_flow(heat_flow_mwm2)

        # Compute lithology features
        features.ultramafic_coverage = ultramafic_pct / 100.0
        features.mafic_coverage = mafic_pct / 100.0
        features.sedimentary_coverage = sedimentary_pct / 100.0

        # Compute topography features
        features.elevation_mean = elevation_m
        features.relief = relief_m
        features.slope = min(1.0, slope_deg / 45.0)  # Normalize by ~45° max slope

        # Compute composite normalized scores (0-1)
        features.f_generation = self._compute_f_generation(features)
        features.f_fluid_interaction = self._compute_f_fluid_interaction(features)
        features.f_structural_pathways = self._compute_f_structural_pathways(features)
        features.f_trap_retention = self._compute_f_trap_retention(features)
        features.f_surface_indicators = self._compute_f_surface_indicators(features)
        features.f_thermodynamic = self._compute_f_thermodynamic(features)

        return features

    # ========== NORMALIZATION FUNCTIONS ==========

    def _clamp01(self, value: float) -> float:
        """Clamp value to [0, 1]."""
        return max(0.0, min(1.0, value))

    def _normalize_fault_density(self, fault_count: int) -> float:
        """
        Normalize fault count to [0, 1].
        0 faults → 0, 5+ faults → 1.0
        """
        return self._clamp01(fault_count / 5.0)

    def _normalize_anomaly(self, value: float, std_dev: float) -> float:
        """
        Normalize anomaly by standard deviation.
        Z-score: (value - mean) / std
        """
        if std_dev == 0:
            return 0.5
        z_score = abs(value) / std_dev
        return self._clamp01(z_score / 2.0)  # 2 std = 1.0

    def _normalize_heat_flow(self, heat_flow_mwm2: float) -> float:
        """
        Normalize heat flow to [0, 1].
        Typical range: 40-100 mW/m²
        0 mW/m² → 0, 100 mW/m² → 1.0
        """
        return self._clamp01(heat_flow_mwm2 / 100.0)

    def _normalize_proximity(self, distance_km: float, max_distance_km: float) -> float:
        """
        Proximity score: 1.0 at distance=0, 0.0 at max_distance.
        """
        if distance_km <= 0:
            return 1.0
        if distance_km >= max_distance_km:
            return 0.0
        return self._clamp01(1.0 - (distance_km / max_distance_km))

    # ========== FEATURE COMPUTATION ==========

    def _compute_structural_complexity(
        self,
        fault_count: int,
        fold_count: int,
        fault_intersections: int
    ) -> float:
        """
        Composite structural complexity: 0.3×faults + 0.4×folds + 0.3×intersections
        """
        fault_score = self._clamp01(fault_count / 5.0)
        fold_score = self._clamp01(fold_count / 3.0)
        intersection_score = self._clamp01(fault_intersections / 3.0)

        return 0.3 * fault_score + 0.4 * fold_score + 0.3 * intersection_score

    def _compute_gravity_gradient(self, gravity_value: float) -> float:
        """
        Gravity gradient indicator: large anomalies suggest density contrasts.
        """
        return self._clamp01(abs(gravity_value) / 100.0)

    def _compute_magnetic_gradient(self, magnetic_value: float) -> float:
        """
        Magnetic gradient indicator: strong anomalies suggest magnetic minerals.
        """
        return self._clamp01(abs(magnetic_value) / 1000.0)

    # ========== COMPOSITE FACTORS (0-1) ==========

    def _compute_f_generation(self, f: GridCellFeatures) -> float:
        """
        Hydrogen generation potential.
        Driven by: ultramafic rocks, heat flow, depth
        """
        return self._clamp01(
            0.4 * f.ultramafic_coverage +
            0.3 * f.heat_flow_indicator +
            0.3 * self._normalize_proximity(f.ultramafic_proximity_km, 100)
        )

    def _compute_f_fluid_interaction(self, f: GridCellFeatures) -> float:
        """
        Fluid circulation capability.
        Driven by: gravity/magnetic anomalies (density contrasts), heat flow
        """
        return self._clamp01(
            0.35 * f.gravity_anomaly +
            0.35 * f.magnetic_anomaly +
            0.3 * f.heat_flow_indicator
        )

    def _compute_f_structural_pathways(self, f: GridCellFeatures) -> float:
        """
        Structural permeability for fluid migration.
        Driven by: faults, structural complexity
        """
        return self._clamp01(
            0.5 * f.fault_density +
            0.5 * f.structural_complexity
        )

    def _compute_f_trap_retention(self, f: GridCellFeatures) -> float:
        """
        Trapping geometry and seal integrity.
        Driven by: folds, structural complexity, sedimentary cover
        """
        return self._clamp01(
            0.4 * f.structural_complexity +
            0.4 * f.gravity_anomaly +
            0.2 * f.sedimentary_coverage
        )

    def _compute_f_surface_indicators(self, f: GridCellFeatures) -> float:
        """
        Known surface indicators: seeps, anomalies.
        Driven by: proximity to known seeps
        """
        seep_score = self._normalize_proximity(f.seep_proximity_km, 100)
        return self._clamp01(seep_score)

    def _compute_f_thermodynamic(self, f: GridCellFeatures) -> float:
        """
        Thermodynamic favorability for hydrogen.
        Driven by: geothermal gradient, heat flow
        """
        return self._clamp01(
            0.5 * f.heat_flow_indicator +
            0.5 * (f.geothermal_gradient / 100.0)  # Normalize to ~100°C/km max
        )

    # ========== BATCH PROCESSING ==========

    def features_to_dict(self, features: GridCellFeatures) -> Dict:
        """Convert GridCellFeatures to dictionary for database storage."""
        return {
            "cell_id": str(features.cell_id),
            "basin_id": str(features.basin_id),
            # Structural
            "fault_density": round(features.fault_density, 4),
            "fault_intersection_count": features.fault_intersection_count,
            "structural_complexity": round(features.structural_complexity, 4),
            # Proximity
            "ultramafic_proximity": round(features.ultramafic_proximity_km, 2),
            "seep_proximity": round(features.seep_proximity_km, 2),
            "fold_proximity": round(features.fold_proximity_km, 2),
            # Anomalies
            "gravity_anomaly": round(features.gravity_anomaly, 4),
            "gravity_gradient": round(features.gravity_gradient, 4),
            "magnetic_anomaly": round(features.magnetic_anomaly, 4),
            "magnetic_gradient": round(features.magnetic_gradient, 4),
            # Thermal
            "heat_flow_indicator": round(features.heat_flow_indicator, 4),
            "heat_flow_value": round(features.heat_flow_value, 2),
            "geothermal_gradient": round(features.geothermal_gradient, 2),
            # Lithology
            "ultramafic_coverage": round(features.ultramafic_coverage, 4),
            "mafic_coverage": round(features.mafic_coverage, 4),
            "sedimentary_coverage": round(features.sedimentary_coverage, 4),
            # Topography
            "elevation_mean": round(features.elevation_mean, 2),
            "relief": round(features.relief, 2),
            "slope": round(features.slope, 4),
            # Composite factors
            "f_generation": round(features.f_generation, 4),
            "f_fluid_interaction": round(features.f_fluid_interaction, 4),
            "f_structural_pathways": round(features.f_structural_pathways, 4),
            "f_trap_retention": round(features.f_trap_retention, 4),
            "f_surface_indicators": round(features.f_surface_indicators, 4),
            "f_thermodynamic": round(features.f_thermodynamic, 4),
        }
