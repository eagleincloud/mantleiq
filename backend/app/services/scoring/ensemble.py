"""
Ensemble scoring: hybrid rule-based + ML model combination.
Implements confidence-adjusted scoring methodology.
"""

from dataclasses import dataclass
from typing import Optional
import logging
import math

from .normalization import clamp01
from .rule_scorer import RuleScorer, FeatureScores
from .completeness import calculate_data_completeness, DataCompletenessResult

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceComponents:
    """Components of the confidence score."""
    data_coverage: float  # Fraction of required data layers available
    data_quality: float  # Quality of available data (1-5 scale normalized)
    missing_completeness: float  # Inverse of missing data penalty


@dataclass
class EnsembleScore:
    """Final ensemble scoring result."""
    rule_score: float  # Pure rule-based score [0, 1]
    ml_score: Optional[float]  # ML model prediction [0, 1] (None if model unavailable)
    ensemble_score: float  # Hybrid combination [0, 1]

    confidence_raw: float  # Raw confidence before modifier
    confidence_adjusted: float  # Confidence with data completeness penalty [0.5, 1.0]
    confidence_components: ConfidenceComponents

    final_score: float  # ensemble_score * confidence_adjusted
    final_rank: int  # Percentile rank [0-100]

    rule_components: dict  # {factor_name: weighted_value} from rule scorer


class EnsembleScorer:
    """
    Hybrid ensemble scoring: 60% rule-based + 40% ML model.
    Applies confidence modifier to account for data completeness.

    Confidence formula:
    C = 0.5 + 0.5 × (0.40 × data_coverage + 0.40 × data_quality + 0.20 × missing_completeness)

    This ensures:
    - Low data: confidence ≥ 0.5 (conservative estimate)
    - Complete data: confidence ≤ 1.0 (full weight)
    """

    def __init__(self, config: dict, rule_scorer: RuleScorer):
        """
        Initialize ensemble scorer.

        Args:
            config: Model config with ensemble weights
            rule_scorer: RuleScorer instance for rule-based component
        """
        self.config = config
        self.rule_scorer = rule_scorer
        self.rule_weight = config.get("ensemble", {}).get("rule_weight", 0.60)
        self.ml_weight = config.get("ensemble", {}).get("ml_weight", 0.40)

        # Normalize weights
        total = self.rule_weight + self.ml_weight
        if total > 0:
            self.rule_weight /= total
            self.ml_weight /= total

        logger.info(f"Ensemble weights: rule={self.rule_weight:.2f}, ml={self.ml_weight:.2f}")

    def score(
        self,
        features: FeatureScores,
        ml_score: Optional[float] = None,
        confidence_components: Optional[ConfidenceComponents] = None,
    ) -> EnsembleScore:
        """
        Compute ensemble score with confidence adjustment.

        Args:
            features: Normalized feature scores
            ml_score: ML model prediction [0, 1], or None if unavailable
            confidence_components: Data quality/coverage components

        Returns:
            EnsembleScore with final score and confidence
        """
        # Rule-based component
        rule_result = self.rule_scorer.score(features)
        rule_score = rule_result.weighted_score

        # ML component (default to rule score if unavailable)
        ml_score_val = clamp01(ml_score) if ml_score is not None else rule_score

        # Ensemble combination
        ensemble_score = self.rule_weight * rule_score + self.ml_weight * ml_score_val
        ensemble_score = clamp01(ensemble_score)

        # Confidence calculation
        if confidence_components is None:
            confidence_components = ConfidenceComponents(
                data_coverage=0.7,
                data_quality=0.7,
                missing_completeness=0.8,
            )

        confidence_raw = (
            0.40 * clamp01(confidence_components.data_coverage)
            + 0.40 * clamp01(confidence_components.data_quality)
            + 0.20 * clamp01(confidence_components.missing_completeness)
        )

        # Confidence is bounded [0.5, 1.0]
        confidence_adjusted = 0.5 + 0.5 * confidence_raw

        # Final score: apply confidence modifier
        final_score = ensemble_score * confidence_adjusted
        final_score = clamp01(final_score)

        # Convert to percentile rank [0-100]
        final_rank = int(round(final_score * 100))

        return EnsembleScore(
            rule_score=rule_score,
            ml_score=clamp01(ml_score) if ml_score is not None else None,
            ensemble_score=ensemble_score,
            confidence_raw=confidence_raw,
            confidence_adjusted=confidence_adjusted,
            confidence_components=confidence_components,
            final_score=final_score,
            final_rank=final_rank,
            rule_components=rule_result.component_dict,
        )

    def score_with_completeness(
        self,
        features: FeatureScores,
        ml_score: Optional[float] = None,
        basin_id: Optional[str] = None,
        session=None,
        layers_dict: Optional[dict] = None,
    ) -> EnsembleScore:
        """
        Compute ensemble score with real data completeness calculation.

        Args:
            features: Normalized feature scores
            ml_score: ML model prediction [0, 1]
            basin_id: Basin UUID for database query
            session: SQLAlchemy session (if basin_id provided)
            layers_dict: Optional dict of layer availability for testing

        Returns:
            EnsembleScore with real confidence from completeness calculation
        """
        # Calculate real completeness
        completeness_result = calculate_data_completeness(
            basin_id=basin_id,
            session=session,
            layers_status=layers_dict
        )

        # Create confidence components from result
        confidence_components = ConfidenceComponents(
            data_coverage=completeness_result.data_coverage,
            data_quality=completeness_result.data_quality,
            missing_completeness=completeness_result.missing_completeness,
        )

        # Score with calculated confidence
        return self.score(features, ml_score, confidence_components)

    def score_dict(
        self,
        feature_dict: dict,
        ml_score: Optional[float] = None,
        coverage: float = 0.7,
        quality: float = 0.7,
        completeness: float = 0.8,
    ) -> EnsembleScore:
        """
        Convenience method: score from dictionary inputs.

        Args:
            feature_dict: Feature values (keys match FeatureScores fields)
            ml_score: Optional ML prediction
            coverage: Data coverage [0, 1]
            quality: Data quality [0, 1]
            completeness: Missing data completeness [0, 1]
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

        confidence = ConfidenceComponents(
            data_coverage=coverage,
            data_quality=quality,
            missing_completeness=completeness,
        )

        return self.score(features, ml_score, confidence)

    def explain_score(self, score_result: EnsembleScore) -> dict:
        """
        Generate human-readable explanation of score components.

        Returns:
            Dict with top factors, confidence breakdown, missing data notes
        """
        # Top 3 contributing factors from rule model
        sorted_factors = sorted(
            score_result.rule_components.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        top_factors = [
            {"factor": name, "contribution": value, "percent": round(100 * value / score_result.ensemble_score, 1)}
            if score_result.ensemble_score > 0
            else {"factor": name, "contribution": value, "percent": 0}
            for name, value in sorted_factors
        ]

        # Confidence breakdown
        conf_comp = score_result.confidence_components
        confidence_notes = []
        if conf_comp.data_coverage < 0.6:
            confidence_notes.append(f"Limited data coverage ({conf_comp.data_coverage:.0%})")
        if conf_comp.data_quality < 0.6:
            confidence_notes.append(f"Lower data quality ({conf_comp.data_quality:.0%})")
        if conf_comp.missing_completeness < 0.7:
            confidence_notes.append("Significant missing data layers")

        return {
            "final_score": round(score_result.final_score, 3),
            "final_rank": score_result.final_rank,
            "score_components": {
                "rule_based": round(score_result.rule_score, 3),
                "ml_model": round(score_result.ml_score, 3) if score_result.ml_score else None,
                "ensemble": round(score_result.ensemble_score, 3),
            },
            "confidence": {
                "adjusted": round(score_result.confidence_adjusted, 3),
                "coverage": f"{conf_comp.data_coverage:.0%}",
                "quality": f"{conf_comp.data_quality:.0%}",
                "completeness": f"{conf_comp.missing_completeness:.0%}",
            },
            "top_factors": top_factors,
            "confidence_notes": confidence_notes,
        }
