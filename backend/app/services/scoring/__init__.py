"""
Scoring service for prospectivity analysis.
Implements rule-based, ML, and ensemble scoring methodologies.
"""

from .normalization import clamp01, linear_normalize, inverse_distance_weight, sigmoid_normalize
from .rule_scorer import RuleScorer, RuleBasedScore, FeatureScores
from .ensemble import EnsembleScorer, EnsembleScore, ConfidenceComponents

__all__ = [
    "clamp01",
    "linear_normalize",
    "inverse_distance_weight",
    "sigmoid_normalize",
    "RuleScorer",
    "RuleBasedScore",
    "FeatureScores",
    "EnsembleScorer",
    "EnsembleScore",
    "ConfidenceComponents",
]
