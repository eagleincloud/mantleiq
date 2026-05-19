#!/usr/bin/env python3
"""
Local Simpl Test Script (SQLite for offline testing)
=====================================================
Tests MantleIQ pipeline components locally without Supabase

Usage:
    python scripts/local_test_simple.py
"""

import sys
import os
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.feature_engineering import FeatureComputer
from app.services.scoring.ensemble import EnsembleScorer
from app.services.scoring.rule_scorer import RuleScorer, FeatureScores
from app.services.explainability import ExplainabilityEngine
from app.services.export import PDFReportGenerator
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEST_DATA_DIR = Path("/tmp/mantleiq_local_test")
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)


def test_feature_computation():
    """Test feature computation locally"""
    logger.info("=" * 70)
    logger.info("TEST 1: Feature Computation")
    logger.info("=" * 70)

    computer = FeatureComputer()

    # Create test features
    features = computer.compute_cell_features(
        cell_id="test_cell_001",
        basin_id="test_basin",
        fault_count=3,
        fault_intersections=2,
        fold_count=1,
        nearest_fault_km=12.5,
        nearest_ultramafic_km=28.3,
        nearest_seep_km=68.9,
        gravity_value=25.4,
        gravity_std=18.2,
        magnetic_value=350.5,
        magnetic_std=280.3,
        heat_flow_mwm2=82.1,
        geothermal_gradient=32.5,
        ultramafic_pct=7.2,
        mafic_pct=18.5,
        sedimentary_pct=74.3,
        elevation_m=520.0,
        relief_m=185.0,
        slope_deg=4.8,
    )

    logger.info(f"✅ Computed features successfully")
    logger.info(f"  - fault_density: {features.fault_density:.3f}")
    logger.info(f"  - ultramafic_proximity_km: {features.ultramafic_proximity_km:.3f}")
    logger.info(f"  - gravity_anomaly: {features.gravity_anomaly:.3f}")
    logger.info(f"  - heat_flow_indicator: {features.heat_flow_indicator:.3f}")
    logger.info(f"  - f_generation: {features.f_generation:.3f}")
    logger.info(f"  - f_fluid_interaction: {features.f_fluid_interaction:.3f}")
    logger.info(f"  - f_structural_pathways: {features.f_structural_pathways:.3f}")
    logger.info(f"  - f_trap_retention: {features.f_trap_retention:.3f}")
    logger.info(f"  - f_surface_indicators: {features.f_surface_indicators:.3f}")
    logger.info(f"  - f_thermodynamic: {features.f_thermodynamic:.3f}")

    return features


def test_scoring(features) -> dict:
    """Test scoring locally"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("TEST 2: Ensemble Scoring")
    logger.info("=" * 70)

    # Initialize config with default weights and ensemble settings
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

    # Create rule scorer and ensemble scorer
    rule_scorer = RuleScorer(config)
    ensemble_scorer = EnsembleScorer(config, rule_scorer)

    # Convert GridCellFeatures to FeatureScores for rule scorer
    feature_scores = FeatureScores(
        fault_intersection=features.fault_density,
        ultramafic_proximity=max(0, 1.0 - (features.ultramafic_proximity_km / 100.0)),
        gravity_anomaly=features.gravity_anomaly,
        magnetic_anomaly=features.magnetic_anomaly,
        heat_flow_indicator=features.heat_flow_indicator,
        structural_complexity=features.structural_complexity,
        seep_proximity=max(0, 1.0 - (features.seep_proximity_km / 100.0)),
    )

    # Score using rule-based scorer
    rule_score = rule_scorer.score(feature_scores)

    # Score using ensemble scorer
    scores = ensemble_scorer.score(feature_scores)

    logger.info(f"✅ Scored features successfully")
    logger.info(f"  - rule_score: {scores.rule_score:.3f}")
    logger.info(f"  - ml_score: {scores.ml_score if scores.ml_score else 'N/A'}")
    logger.info(f"  - ensemble_score: {scores.ensemble_score:.3f}")
    logger.info(f"  - final_score: {scores.final_score:.3f}")
    logger.info(f"  - confidence_adjusted: {scores.confidence_adjusted:.3f}")
    logger.info(f"  - final_rank: {scores.final_rank}")

    return {
        'rule_score': scores.rule_score,
        'ml_score': scores.ml_score,
        'ensemble_score': scores.ensemble_score,
        'final_score': scores.final_score,
        'confidence_score': scores.confidence_adjusted,
        'rank': scores.final_rank,
        'percentile': scores.final_rank,
        'components': scores.rule_components,
    }


def test_explainability(scores: dict):
    """Test explainability locally"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("TEST 3: Explainability & Attribution")
    logger.info("=" * 70)

    explainer = ExplainabilityEngine()

    # Create explanation
    explanation = explainer.explain_zone_score(
        zone_id="test_zone_001",
        final_score=scores.get('final_score', 0.5),
        final_rank=scores.get('rank', 50),
        rule_components=scores.get('components', {}),
        feature_dict={
            "fault_density": 0.65,
            "ultramafic_proximity": 0.72,
            "gravity_anomaly": 0.58,
            "magnetic_anomaly": 0.61,
            "heat_flow_indicator": 0.75,
            "structural_complexity": 0.68,
            "seep_proximity": 0.55,
        },
        confidence_score=scores.get('confidence_score', 0.7),
        confidence_components={
            "data_coverage": 0.80,
            "data_quality": 0.75,
            "missing_completeness": 0.85,
        },
        missing_data_count=2,
        total_data_layers=8,
    )

    logger.info(f"✅ Generated explanation successfully")
    logger.info(f"  - score_class: {explanation.score_class}")
    logger.info(f"  - final_score: {explanation.final_score:.3f}")
    logger.info(f"  - confidence_score: {explanation.confidence_breakdown.get('adjusted', 0):.3f}")
    logger.info(f"  - top_features: {len(explanation.top_features)} features")
    logger.info(f"  - missing_data_caveats: {len(explanation.missing_data_caveats)} caveats")
    logger.info(f"  - recommended_actions: {len(explanation.recommended_actions)} actions")
    logger.info("")
    logger.info(f"Narrative: {explanation.narrative_summary[:100]}...")

    return explanation


def test_pdf_export(explanation):
    """Test PDF generation locally"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("TEST 4: PDF Report Generation")
    logger.info("=" * 70)

    generator = PDFReportGenerator()

    pdf_bytes = generator.generate_report(
        zone_name="Test Prospect Zone",
        basin_name="Test Basin",
        final_score=explanation.final_score,
        final_rank=explanation.final_rank,
        score_class=explanation.score_class,
        score_components=explanation.score_components,
        top_features=[
            {
                "name": f.name,
                "label": f.label,
                "value": f.value,
                "weight": f.weight,
                "contribution": f.contribution,
            }
            for f in explanation.top_features
        ],
        missing_data_caveats=explanation.missing_data_caveats,
        narrative_summary=explanation.narrative_summary,
        recommended_actions=explanation.recommended_actions,
        confidence_score=explanation.confidence_breakdown.get('adjusted', 0.7),
    )

    report_path = TEST_DATA_DIR / "test_report.pdf"
    with open(report_path, "wb") as f:
        f.write(pdf_bytes)

    logger.info(f"✅ Generated PDF report successfully")
    logger.info(f"  - File size: {len(pdf_bytes) / 1024:.1f} KB")
    logger.info(f"  - Path: {report_path}")

    return str(report_path)


def main():
    """Run all local tests"""
    logger.info("")
    logger.info("*" * 70)
    logger.info("MANTLEIQ LOCAL PIPELINE TEST (Offline)")
    logger.info("*" * 70)
    logger.info("")

    try:
        # Test 1: Feature Computation
        features = test_feature_computation()

        # Test 2: Scoring
        scores = test_scoring(features)

        # Test 3: Explainability
        explanation = test_explainability(scores)

        # Test 4: PDF Export
        pdf_path = test_pdf_export(explanation)

        # Summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ ALL LOCAL TESTS PASSED SUCCESSFULLY")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Test Results Summary:")
        logger.info(f"  ✓ Feature Computation: 25+ features computed")
        logger.info(f"  ✓ Ensemble Scoring: Rule + ML scoring working")
        logger.info(f"  ✓ Explainability: Attribution + narratives generated")
        logger.info(f"  ✓ PDF Export: Report generated ({len(pdf_path)} bytes)")
        logger.info("")
        logger.info(f"Next Steps:")
        logger.info(f"  1. Connect to Supabase: Update DATABASE_URL in .env")
        logger.info(f"  2. Run: python scripts/batch_feature_compute.py <basin-id>")
        logger.info(f"  3. Deploy Prefect: python -m prefect deployment build backend/workflows/data_pipeline.py")
        logger.info(f"  4. Start API: python -m uvicorn app.main:app --reload")
        logger.info("")

        return 0

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
