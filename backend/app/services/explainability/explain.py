"""
Explainability service: generate human-readable score attribution and narratives.
SHAP values, feature contributions, missing data caveats, and recommendations.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeatureAttribution:
    """Single feature contribution to score."""
    name: str
    label: str
    value: float
    weight: float
    contribution: float  # percentage


@dataclass
class ScoreExplanation:
    """Complete score explanation with attribution and recommendations."""
    final_score: float
    final_rank: int
    score_class: str

    top_features: List[FeatureAttribution]
    missing_data_caveats: List[str]
    narrative_summary: str
    recommended_actions: List[str]

    score_components: Dict[str, float]  # {f_generation, f_fluid_interaction, ...}
    confidence_breakdown: Dict[str, float]


class ExplainabilityEngine:
    """
    Generate human-readable explanations for prospectivity scores.

    Features:
    - Top contributing factors (SHAP-inspired)
    - Missing data penalties
    - Natural language narratives
    - Actionable recommendations
    """

    def __init__(self):
        """Initialize explainability engine with label mappings."""
        self.feature_labels = {
            "fault_density": "Fault Intersection Density",
            "ultramafic_proximity": "Ultramafic Rock Proximity",
            "gravity_anomaly": "Gravity Anomaly Strength",
            "magnetic_anomaly": "Magnetic Anomaly Strength",
            "heat_flow_indicator": "Geothermal Favorability",
            "structural_complexity": "Structural Complexity Index",
            "seep_proximity": "Known H₂ Seeps & Anomalies",
            "sedimentary_coverage": "Sedimentary Basin Cover",
            "f_generation": "Hydrogen Generation Potential",
            "f_fluid_interaction": "Fluid Circulation Capability",
            "f_structural_pathways": "Structural Permeability",
            "f_trap_retention": "Trap Integrity & Sealing",
            "f_surface_indicators": "Surface Evidence",
            "f_thermodynamic": "Temperature Window Favorability",
        }

        self.score_classes = {
            (80, 100): "High-priority target",
            (65, 79): "Strong prospect, needs validation",
            (50, 64): "Moderate prospect",
            (35, 49): "Weak / speculative",
            (0, 34): "Low priority",
        }

    def explain_zone_score(
        self,
        zone_id: str,
        final_score: float,
        final_rank: int,
        rule_components: Dict[str, float],
        feature_dict: Dict[str, float],
        confidence_score: float,
        confidence_components: Dict[str, float],
        missing_data_count: int = 0,
        total_data_layers: int = 8,
    ) -> ScoreExplanation:
        """
        Generate comprehensive explanation for a zone's prospectivity score.

        Args:
            zone_id: Zone UUID
            final_score: Final score [0, 1]
            final_rank: Percentile rank [0-100]
            rule_components: {f_generation, f_fluid_interaction, ...}
            feature_dict: All computed feature values
            confidence_score: Confidence modifier [0.5, 1.0]
            confidence_components: {coverage, quality, completeness}
            missing_data_count: Number of missing data layers
            total_data_layers: Total expected layers

        Returns:
            ScoreExplanation with all attribution and recommendations
        """
        # Interpret score
        score_class = self._get_score_class(final_score * 100)

        # Extract top contributing features
        top_features = self._rank_features(
            feature_dict, rule_components
        )

        # Generate missing data caveats
        caveats = self._generate_data_caveats(
            missing_data_count, total_data_layers, confidence_score
        )

        # Generate narrative summary
        narrative = self._generate_narrative(
            final_score * 100, score_class, top_features, caveats
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            final_score * 100, top_features, caveats
        )

        return ScoreExplanation(
            final_score=round(final_score, 4),
            final_rank=final_rank,
            score_class=score_class,
            top_features=top_features[:4],  # Top 4 only
            missing_data_caveats=caveats,
            narrative_summary=narrative,
            recommended_actions=recommendations,
            score_components={
                k: round(v, 4) for k, v in rule_components.items()
            },
            confidence_breakdown={
                "adjusted": round(confidence_score, 3),
                "coverage": round(confidence_components.get("data_coverage", 0.7), 3),
                "quality": round(confidence_components.get("data_quality", 0.7), 3),
                "completeness": round(
                    confidence_components.get("missing_completeness", 0.8), 3
                ),
            },
        )

    def _get_score_class(self, score: float) -> str:
        """Map score to interpretation class."""
        for (low, high), label in sorted(
            self.score_classes.items(), reverse=True
        ):
            if low <= score <= high:
                return label
        return "Unknown"

    def _rank_features(
        self,
        feature_dict: Dict[str, float],
        rule_components: Dict[str, float],
    ) -> List[FeatureAttribution]:
        """
        Rank features by contribution to final score.

        Uses rule component weights to determine importance.
        """
        # Map features to rule factors
        feature_to_factors = {
            "fault_density": ["f_generation", "f_structural_pathways"],
            "seep_proximity": ["f_generation", "f_surface_indicators"],
            "gravity_anomaly": ["f_fluid_interaction", "f_trap_retention"],
            "magnetic_anomaly": ["f_fluid_interaction"],
            "heat_flow_indicator": ["f_thermodynamic"],
            "structural_complexity": [
                "f_structural_pathways", "f_trap_retention"
            ],
            "ultramafic_proximity": ["f_generation"],
        }

        # Compute contribution for each feature
        contributions = []
        total_contribution = sum(rule_components.values())

        for feature_name, feature_value in feature_dict.items():
            if feature_name not in feature_to_factors:
                continue

            # Sum contributions from associated factors
            factor_contribution = sum(
                rule_components.get(factor, 0)
                for factor in feature_to_factors[feature_name]
            )

            if factor_contribution > 0:
                pct_contribution = (
                    100 * factor_contribution / total_contribution
                    if total_contribution > 0
                    else 0
                )

                attribution = FeatureAttribution(
                    name=feature_name,
                    label=self.feature_labels.get(
                        feature_name, feature_name.replace("_", " ").title()
                    ),
                    value=round(feature_value, 3),
                    weight=round(factor_contribution, 3),
                    contribution=round(pct_contribution, 1),
                )
                contributions.append(attribution)

        # Sort by contribution (descending)
        contributions.sort(key=lambda x: x.contribution, reverse=True)

        return contributions

    def _generate_data_caveats(
        self,
        missing_count: int,
        total_layers: int,
        confidence: float,
    ) -> List[str]:
        """Generate caveats about data quality and completeness."""
        caveats = []

        # Data coverage caveats
        coverage = 1.0 - (missing_count / total_layers)
        if coverage < 0.6:
            caveats.append(
                f"Limited data coverage ({coverage:.0%} of required layers)"
            )
        elif coverage < 0.8:
            caveats.append(
                f"Data coverage moderate ({coverage:.0%}) - key layers missing"
            )

        # Confidence-based caveats
        if confidence < 0.6:
            caveats.append("Low confidence due to incomplete or poor-quality data")
        elif confidence < 0.7:
            caveats.append("Moderate confidence - recommend field verification")

        # Missing data types
        if missing_count > 0:
            caveats.append(
                f"{missing_count} expected data layer(s) unavailable for this region"
            )

        return caveats

    def _generate_narrative(
        self,
        score: float,
        score_class: str,
        top_features: List[FeatureAttribution],
        caveats: List[str],
    ) -> str:
        """Generate natural language summary of the score."""
        narrative = f"Zone scored {score:.1f}th percentile ({score_class}). "

        if top_features:
            feature_phrases = [
                f"{f.label.lower()} ({f.contribution:.0f}%)"
                for f in top_features[:3]
            ]
            features_text = ", ".join(feature_phrases)
            narrative += f"Driven by: {features_text}. "

        if caveats:
            caveats_text = " ".join(caveats)
            narrative += f"⚠️ {caveats_text}"

        return narrative.strip()

    def _generate_recommendations(
        self,
        score: float,
        top_features: List[FeatureAttribution],
        caveats: List[str],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # High-priority targets
        if score >= 80:
            recommendations.append("Prioritize for drilling prospects")
            recommendations.append("Acquire high-resolution seismic data")

        # Strong prospects
        elif score >= 65:
            recommendations.append("Conduct detailed geological mapping")
            recommendations.append("Perform pressure-temperature modeling")

        # Moderate prospects
        elif score >= 50:
            recommendations.append("Assess economic viability")
            recommendations.append("Study analog basin analogs")

        # Weak prospects
        else:
            recommendations.append("Monitor for additional data")
            recommendations.append("Consider for future re-evaluation")

        # Data-driven recommendations
        if "seismic" in str(caveats).lower():
            recommendations.append("Acquire seismic reflection survey")

        if any("gravity" in c.lower() for c in caveats):
            recommendations.append("Conduct additional gravity survey")

        if any("magnetic" in c.lower() for c in caveats):
            recommendations.append("Perform magnetic survey")

        if any("heat flow" in c.lower() for c in caveats):
            recommendations.append("Collect thermal gradient measurements")

        # Feature-based recommendations
        for feature in top_features[:2]:
            if "fault" in feature.name.lower():
                recommendations.append("Conduct fault mapping and characterization")
            if "seep" in feature.name.lower():
                recommendations.append("Investigate surface seepage sites")
            if "ultramafic" in feature.name.lower():
                recommendations.append("Validate ultramafic rock presence")

        # Remove duplicates while preserving order
        seen = set()
        unique_recs = []
        for rec in recommendations[:8]:  # Limit to 8 recommendations
            if rec not in seen:
                unique_recs.append(rec)
                seen.add(rec)

        return unique_recs

    def explanation_to_dict(self, explanation: ScoreExplanation) -> Dict:
        """Convert ScoreExplanation to dictionary for database storage."""
        return {
            "final_score": explanation.final_score,
            "final_rank": explanation.final_rank,
            "score_class": explanation.score_class,
            "top_features": [
                {
                    "name": f.name,
                    "label": f.label,
                    "value": f.value,
                    "weight": f.weight,
                    "contribution": f.contribution,
                }
                for f in explanation.top_features
            ],
            "missing_data_caveats": explanation.missing_data_caveats,
            "narrative_summary": explanation.narrative_summary,
            "recommended_actions": explanation.recommended_actions,
            "score_components": explanation.score_components,
            "confidence_breakdown": explanation.confidence_breakdown,
        }
