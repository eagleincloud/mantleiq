"""
Rule-based prospectivity scoring using weighted geospatial features.
Implements the 6-factor scoring methodology.
"""

from dataclasses import dataclass
from typing import Optional
import logging

from .normalization import clamp01

logger = logging.getLogger(__name__)


@dataclass
class FeatureScores:
    """Normalized feature scores [0, 1]."""
    fault_intersection: float
    ultramafic_proximity: float
    gravity_anomaly: float
    magnetic_anomaly: float
    heat_flow_indicator: float
    structural_complexity: float
    seep_proximity: float


@dataclass
class RuleBasedScore:
    """Rule-based scoring result."""
    f_generation: float  # Hydrogen generation potential (30%)
    f_fluid_interaction: float  # Fluid circulation (20%)
    f_structural_pathways: float  # Structural permeability (20%)
    f_trap_retention: float  # Trapping geometry (15%)
    f_surface_indicators: float  # Known seeps/anomalies (10%)
    f_thermodynamic: float  # Temperature window (5%)

    weighted_score: float  # Sum of all weighted components
    component_dict: dict  # {factor_name: weight * score}


class RuleScorer:
    """
    Rule-based scoring engine using 6-factor weighting methodology.

    Scoring formula:
    weighted_score = Σ(weight_i × F_i)
    where:
      F_generation = (fault_intersection + seep_proximity) / 2
      F_fluid_interaction = (gravity + magnetic anomaly) / 2
      F_structural_pathways = (fault_intersection + structural_complexity) / 2
      F_trap_retention = (structural_complexity + gravity anomaly) / 2
      F_surface_indicators = seep_proximity
      F_thermodynamic = heat_flow_indicator
    """

    def __init__(self, config: dict):
        """
        Initialize with weights from config/model.yaml.

        Expected config keys:
          weights: {
            f_generation, f_fluid_interaction, f_structural_pathways,
            f_trap_retention, f_surface_indicators, f_thermodynamic
          }
        """
        self.weights = config.get("weights", {
            "f_generation": 0.30,
            "f_fluid_interaction": 0.20,
            "f_structural_pathways": 0.20,
            "f_trap_retention": 0.15,
            "f_surface_indicators": 0.10,
            "f_thermodynamic": 0.05,
        })

        # Validate weights sum to 1.0
        weight_sum = sum(self.weights.values())
        if abs(weight_sum - 1.0) > 0.01:
            logger.warning(f"Weights sum to {weight_sum}, normalizing to 1.0")
            for key in self.weights:
                self.weights[key] /= weight_sum

    def score(self, features: FeatureScores) -> RuleBasedScore:
        """
        Compute rule-based score from normalized feature scores.

        Args:
            features: Normalized [0,1] feature scores

        Returns:
            RuleBasedScore with individual factors and weighted sum
        """
        # Compute 6 factors from 7 base features
        f_generation = clamp01((features.fault_intersection + features.seep_proximity) / 2)
        f_fluid_interaction = clamp01((features.gravity_anomaly + features.magnetic_anomaly) / 2)
        f_structural_pathways = clamp01((features.fault_intersection + features.structural_complexity) / 2)
        f_trap_retention = clamp01((features.structural_complexity + features.gravity_anomaly) / 2)
        f_surface_indicators = features.seep_proximity
        f_thermodynamic = features.heat_flow_indicator

        # Apply weights
        component_dict = {
            "f_generation": self.weights["f_generation"] * f_generation,
            "f_fluid_interaction": self.weights["f_fluid_interaction"] * f_fluid_interaction,
            "f_structural_pathways": self.weights["f_structural_pathways"] * f_structural_pathways,
            "f_trap_retention": self.weights["f_trap_retention"] * f_trap_retention,
            "f_surface_indicators": self.weights["f_surface_indicators"] * f_surface_indicators,
            "f_thermodynamic": self.weights["f_thermodynamic"] * f_thermodynamic,
        }

        weighted_score = sum(component_dict.values())

        return RuleBasedScore(
            f_generation=f_generation,
            f_fluid_interaction=f_fluid_interaction,
            f_structural_pathways=f_structural_pathways,
            f_trap_retention=f_trap_retention,
            f_surface_indicators=f_surface_indicators,
            f_thermodynamic=f_thermodynamic,
            weighted_score=clamp01(weighted_score),
            component_dict=component_dict,
        )

    def score_dict(self, feature_dict: dict) -> RuleBasedScore:
        """
        Convenience method: score from dictionary of feature values.

        Expected keys:
          fault_intersection, ultramafic_proximity, gravity_anomaly,
          magnetic_anomaly, heat_flow_indicator, structural_complexity,
          seep_proximity
        """
        features = FeatureScores(
            fault_intersection=clamp01(feature_dict.get("fault_intersection", 0.5)),
            ultramafic_proximity=clamp01(feature_dict.get("ultramafic_proximity", 0.5)),
            gravity_anomaly=clamp01(feature_dict.get("gravity_anomaly", 0.5)),
            magnetic_anomaly=clamp01(feature_dict.get("magnetic_anomaly", 0.5)),
            heat_flow_indicator=clamp01(feature_dict.get("heat_flow_indicator", 0.5)),
            structural_complexity=clamp01(feature_dict.get("structural_complexity", 0.5)),
            seep_proximity=clamp01(feature_dict.get("seep_proximity", 0.5)),
        )
        return self.score(features)
