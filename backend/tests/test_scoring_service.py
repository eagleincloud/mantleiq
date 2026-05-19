"""
Unit tests for scoring service (normalization, rule-based, ensemble).
"""

import pytest
from app.services.scoring import (
    clamp01,
    linear_normalize,
    inverse_distance_weight,
    sigmoid_normalize,
    RuleScorer,
    EnsembleScorer,
    FeatureScores,
    ConfidenceComponents,
)


class TestNormalization:
    """Test normalization utility functions."""

    def test_clamp01_bounds(self):
        """Test clamp01 enforces [0, 1] bounds."""
        assert clamp01(-1.0) == 0.0
        assert clamp01(0.5) == 0.5
        assert clamp01(2.0) == 1.0

    def test_linear_normalize(self):
        """Test linear_normalize maps [min, max] → [0, 1]."""
        assert linear_normalize(0, 0, 100) == 0.0
        assert linear_normalize(50, 0, 100) == 0.5
        assert linear_normalize(100, 0, 100) == 1.0
        assert linear_normalize(150, 0, 100) == 1.0  # Clamped

    def test_inverse_distance_weight(self):
        """Test inverse_distance_weight decreases with distance."""
        assert inverse_distance_weight(0, 100) == 1.0
        assert inverse_distance_weight(50, 100) == 0.5
        assert inverse_distance_weight(100, 100) == 0.0
        assert inverse_distance_weight(150, 100) == 0.0

    def test_sigmoid_normalize(self):
        """Test sigmoid_normalize produces S-curve."""
        # At midpoint, should be ~0.5
        val = sigmoid_normalize(0.5, midpoint=0.5, steepness=10.0)
        assert 0.48 < val < 0.52

        # Below midpoint < 0.5, above > 0.5
        below = sigmoid_normalize(0.3, midpoint=0.5, steepness=10.0)
        above = sigmoid_normalize(0.7, midpoint=0.5, steepness=10.0)
        assert below < 0.5 < above


class TestRuleScorer:
    """Test rule-based scoring."""

    @pytest.fixture
    def rule_scorer(self):
        config = {
            "weights": {
                "f_generation": 0.30,
                "f_fluid_interaction": 0.20,
                "f_structural_pathways": 0.20,
                "f_trap_retention": 0.15,
                "f_surface_indicators": 0.10,
                "f_thermodynamic": 0.05,
            }
        }
        return RuleScorer(config)

    def test_score_all_high(self, rule_scorer):
        """Test scoring when all features are high."""
        features = FeatureScores(
            fault_intersection=1.0,
            ultramafic_proximity=1.0,
            gravity_anomaly=1.0,
            magnetic_anomaly=1.0,
            heat_flow_indicator=1.0,
            structural_complexity=1.0,
            seep_proximity=1.0,
        )
        result = rule_scorer.score(features)

        # All factors should be 1.0, weighted sum should be ~1.0
        assert result.f_generation == 1.0
        assert result.weighted_score == pytest.approx(1.0, abs=0.01)

    def test_score_all_low(self, rule_scorer):
        """Test scoring when all features are low."""
        features = FeatureScores(
            fault_intersection=0.0,
            ultramafic_proximity=0.0,
            gravity_anomaly=0.0,
            magnetic_anomaly=0.0,
            heat_flow_indicator=0.0,
            structural_complexity=0.0,
            seep_proximity=0.0,
        )
        result = rule_scorer.score(features)

        # All factors should be 0.0, weighted sum should be 0.0
        assert result.f_generation == 0.0
        assert result.weighted_score == pytest.approx(0.0, abs=0.01)

    def test_score_mixed(self, rule_scorer):
        """Test scoring with mixed feature values."""
        features = FeatureScores(
            fault_intersection=0.8,
            ultramafic_proximity=0.3,
            gravity_anomaly=0.6,
            magnetic_anomaly=0.7,
            heat_flow_indicator=0.5,
            structural_complexity=0.4,
            seep_proximity=0.2,
        )
        result = rule_scorer.score(features)

        # Verify components are computed
        assert 0 <= result.f_generation <= 1.0
        assert 0 <= result.weighted_score <= 1.0
        assert result.component_dict["f_generation"] == pytest.approx(0.30 * result.f_generation, abs=0.01)

    def test_score_dict(self, rule_scorer):
        """Test scoring from dictionary input."""
        feature_dict = {
            "fault_intersection": 0.8,
            "gravity_anomaly": 0.6,
            "heat_flow_indicator": 0.5,
        }
        result = rule_scorer.score_dict(feature_dict)

        assert 0 <= result.weighted_score <= 1.0


class TestEnsembleScorer:
    """Test ensemble (rule + ML) scoring."""

    @pytest.fixture
    def ensemble_scorer(self):
        config = {
            "weights": {
                "f_generation": 0.30,
                "f_fluid_interaction": 0.20,
                "f_structural_pathways": 0.20,
                "f_trap_retention": 0.15,
                "f_surface_indicators": 0.10,
                "f_thermodynamic": 0.05,
            },
            "ensemble": {
                "rule_weight": 0.60,
                "ml_weight": 0.40,
            }
        }
        rule_scorer = RuleScorer(config)
        return EnsembleScorer(config, rule_scorer)

    def test_ensemble_without_ml(self, ensemble_scorer):
        """Test ensemble scoring when ML model unavailable."""
        features = FeatureScores(
            fault_intersection=0.8,
            ultramafic_proximity=0.5,
            gravity_anomaly=0.6,
            magnetic_anomaly=0.7,
            heat_flow_indicator=0.5,
            structural_complexity=0.4,
            seep_proximity=0.2,
        )
        confidence = ConfidenceComponents(
            data_coverage=0.8,
            data_quality=0.7,
            missing_completeness=0.9,
        )

        result = ensemble_scorer.score(features, ml_score=None, confidence_components=confidence)

        # With no ML score, ensemble = rule score
        assert result.ml_score is None
        assert result.ensemble_score == result.rule_score
        # Final score should be ensemble * confidence
        assert result.final_score == pytest.approx(result.ensemble_score * result.confidence_adjusted, abs=0.01)

    def test_ensemble_with_ml(self, ensemble_scorer):
        """Test ensemble scoring with ML prediction."""
        features = FeatureScores(
            fault_intersection=0.8,
            ultramafic_proximity=0.5,
            gravity_anomaly=0.6,
            magnetic_anomaly=0.7,
            heat_flow_indicator=0.5,
            structural_complexity=0.4,
            seep_proximity=0.2,
        )
        confidence = ConfidenceComponents(
            data_coverage=0.8,
            data_quality=0.7,
            missing_completeness=0.9,
        )

        result = ensemble_scorer.score(features, ml_score=0.9, confidence_components=confidence)

        # Ensemble should be 60% rule + 40% ML
        expected_ensemble = 0.60 * result.rule_score + 0.40 * 0.9
        assert result.ensemble_score == pytest.approx(expected_ensemble, abs=0.01)

    def test_confidence_bounds(self, ensemble_scorer):
        """Test confidence is bounded [0.5, 1.0]."""
        features = FeatureScores(
            fault_intersection=0.5, ultramafic_proximity=0.5, gravity_anomaly=0.5,
            magnetic_anomaly=0.5, heat_flow_indicator=0.5,
            structural_complexity=0.5, seep_proximity=0.5,
        )

        # Low confidence
        result_low = ensemble_scorer.score(
            features,
            confidence_components=ConfidenceComponents(0.2, 0.2, 0.2)
        )
        assert 0.5 <= result_low.confidence_adjusted <= 1.0

        # High confidence
        result_high = ensemble_scorer.score(
            features,
            confidence_components=ConfidenceComponents(1.0, 1.0, 1.0)
        )
        assert result_high.confidence_adjusted == pytest.approx(1.0, abs=0.01)

    def test_final_rank(self, ensemble_scorer):
        """Test final rank is [0-100] percentile."""
        features = FeatureScores(
            fault_intersection=0.8,
            ultramafic_proximity=0.5,
            gravity_anomaly=0.6,
            magnetic_anomaly=0.7,
            heat_flow_indicator=0.5,
            structural_complexity=0.4,
            seep_proximity=0.2,
        )

        result = ensemble_scorer.score(features)

        assert 0 <= result.final_rank <= 100
        assert result.final_rank == int(round(result.final_score * 100))

    def test_explain_score(self, ensemble_scorer):
        """Test score explanation generation."""
        features = FeatureScores(
            fault_intersection=0.8,
            ultramafic_proximity=0.5,
            gravity_anomaly=0.6,
            magnetic_anomaly=0.7,
            heat_flow_indicator=0.5,
            structural_complexity=0.4,
            seep_proximity=0.2,
        )

        result = ensemble_scorer.score(features)
        explanation = ensemble_scorer.explain_score(result)

        assert "final_score" in explanation
        assert "final_rank" in explanation
        assert "score_components" in explanation
        assert "confidence" in explanation
        assert "top_factors" in explanation
        assert len(explanation["top_factors"]) <= 3
