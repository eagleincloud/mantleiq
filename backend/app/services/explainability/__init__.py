"""
Explainability service: generate human-readable score attribution and narratives.
"""

from .explain import ExplainabilityEngine, ScoreExplanation, FeatureAttribution

__all__ = ["ExplainabilityEngine", "ScoreExplanation", "FeatureAttribution"]
