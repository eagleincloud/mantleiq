#!/usr/bin/env python3
"""
Local Pipeline Test with SQLite (No External Dependencies)
==========================================================
Full pipeline test with local SQLite database:
1. Create test basin
2. Create test grid cells
3. Compute features
4. Score zones
5. Generate reports

Usage:
    python scripts/local_test_with_sqlite.py
"""

import sys
import os
import uuid
import json
from pathlib import Path
import logging
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, JSON
from sqlalchemy.orm import Session, declarative_base
from app.services.feature_engineering import FeatureComputer
from app.services.scoring.ensemble import EnsembleScorer
from app.services.scoring.rule_scorer import RuleScorer, FeatureScores
from app.services.explainability import ExplainabilityEngine
from app.services.export import PDFReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEST_DATA_DIR = Path("/tmp/mantleiq_local_test")
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite database path
DB_PATH = TEST_DATA_DIR / "mantleiq_test.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()


class BasinRecord(Base):
    """Test basin record"""
    __tablename__ = "basins"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    region = Column(String, nullable=True)
    country = Column(String, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GridCellRecord(Base):
    """Test grid cell record"""
    __tablename__ = "grid_cells"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    basin_id = Column(String, nullable=False)
    grid_index = Column(Integer, nullable=True)
    centroid_lon = Column(Float, nullable=True)
    centroid_lat = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FeatureRecord(Base):
    """Test feature record"""
    __tablename__ = "features"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    grid_cell_id = Column(String, nullable=False)
    basin_id = Column(String, nullable=False)

    fault_density = Column(Float, nullable=True)
    fault_intersection_count = Column(Integer, nullable=True)
    structural_complexity = Column(Float, nullable=True)
    gravity_anomaly = Column(Float, nullable=True)
    heat_flow_indicator = Column(Float, nullable=True)
    f_generation = Column(Float, nullable=True)
    f_fluid_interaction = Column(Float, nullable=True)
    f_structural_pathways = Column(Float, nullable=True)
    f_trap_retention = Column(Float, nullable=True)
    f_surface_indicators = Column(Float, nullable=True)
    f_thermodynamic = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScoreRecord(Base):
    """Test score record"""
    __tablename__ = "scores"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    grid_cell_id = Column(String, nullable=False)
    basin_id = Column(String, nullable=False)

    rule_score = Column(Float, nullable=True)
    ml_score = Column(Float, nullable=True)
    ensemble_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    components = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


def test_full_pipeline():
    """Run complete local pipeline with SQLite"""
    logger.info("")
    logger.info("*" * 70)
    logger.info("MANTLEIQ LOCAL PIPELINE TEST (SQLite, Offline)")
    logger.info("*" * 70)
    logger.info("")

    # Create database and tables
    if DB_PATH.exists():
        DB_PATH.unlink()

    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            # Step 1: Create test basin
            logger.info("=" * 70)
            logger.info("STEP 1: Create Test Basin")
            logger.info("=" * 70)

            basin = BasinRecord(
                id=str(uuid.uuid4()),
                name="Test Basin - Kansas Rift",
                region="Kansas, USA",
                country="United States",
                description="Test basin for local pipeline validation"
            )
            session.add(basin)
            session.commit()
            session.refresh(basin)
            logger.info(f"✅ Created basin: {basin.name} (ID: {basin.id})")
            basin_id = basin.id

            # Step 2: Create test grid cells
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 2: Create Test Grid Cells")
            logger.info("=" * 70)

            cells = []
            for i in range(5):
                lon = -95.0 + (i % 3) * 0.5
                lat = 38.0 + (i // 3) * 0.5

                cell = GridCellRecord(
                    id=str(uuid.uuid4()),
                    basin_id=basin_id,
                    grid_index=i,
                    centroid_lon=lon,
                    centroid_lat=lat
                )
                session.add(cell)
                cells.append(cell)

            session.commit()
            logger.info(f"✅ Created {len(cells)} grid cells")

            # Step 3: Compute features
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 3: Compute Features")
            logger.info("=" * 70)

            computer = FeatureComputer()

            for idx, cell in enumerate(cells, 1):
                features = computer.compute_cell_features(
                    cell_id=cell.id,
                    basin_id=basin_id,
                    fault_count=2 + (idx % 3),
                    fault_intersections=1,
                    fold_count=1,
                    nearest_fault_km=15.0 - (idx % 5),
                    nearest_ultramafic_km=30.0 + (idx % 10),
                    nearest_seep_km=75.0 - (idx % 20),
                    gravity_value=20.0 + (idx % 20),
                    gravity_std=15.0,
                    magnetic_value=300.0 + (idx % 100),
                    magnetic_std=250.0,
                    heat_flow_mwm2=75.0 + (idx % 20),
                    geothermal_gradient=30.0,
                    ultramafic_pct=5.0 + (idx % 8),
                    mafic_pct=15.0 + (idx % 10),
                    sedimentary_pct=80.0 - (idx % 15),
                    elevation_m=500.0 + (idx % 500),
                    relief_m=200.0,
                    slope_deg=5.0,
                )

                feature_record = FeatureRecord(
                    id=str(uuid.uuid4()),
                    grid_cell_id=cell.id,
                    basin_id=basin_id,
                    fault_density=features.fault_density,
                    fault_intersection_count=features.fault_intersection_count,
                    structural_complexity=features.structural_complexity,
                    gravity_anomaly=features.gravity_anomaly,
                    heat_flow_indicator=features.heat_flow_indicator,
                    f_generation=features.f_generation,
                    f_fluid_interaction=features.f_fluid_interaction,
                    f_structural_pathways=features.f_structural_pathways,
                    f_trap_retention=features.f_trap_retention,
                    f_surface_indicators=features.f_surface_indicators,
                    f_thermodynamic=features.f_thermodynamic,
                )
                session.add(feature_record)

            session.commit()
            logger.info(f"✅ Computed features for {len(cells)} cells")

            # Step 4: Score cells
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 4: Score Grid Cells")
            logger.info("=" * 70)

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
            ensemble_scorer = EnsembleScorer(config, rule_scorer)

            for cell in cells:
                feature_record = session.query(FeatureRecord).filter(
                    FeatureRecord.grid_cell_id == cell.id
                ).first()

                if not feature_record:
                    continue

                feature_scores = FeatureScores(
                    fault_intersection=feature_record.fault_density,
                    ultramafic_proximity=0.7,
                    gravity_anomaly=feature_record.gravity_anomaly,
                    magnetic_anomaly=0.6,
                    heat_flow_indicator=feature_record.heat_flow_indicator,
                    structural_complexity=feature_record.structural_complexity,
                    seep_proximity=0.5,
                )

                scores = ensemble_scorer.score(feature_scores)

                score_record = ScoreRecord(
                    id=str(uuid.uuid4()),
                    grid_cell_id=cell.id,
                    basin_id=basin_id,
                    rule_score=scores.rule_score,
                    ml_score=scores.ml_score,
                    ensemble_score=scores.ensemble_score,
                    final_score=scores.final_score,
                    confidence_score=scores.confidence_adjusted,
                    rank=scores.final_rank,
                    components=scores.rule_components,
                )
                session.add(score_record)

            session.commit()
            logger.info(f"✅ Scored {len(cells)} cells")

            # Step 5: Generate report
            logger.info("")
            logger.info("=" * 70)
            logger.info("STEP 5: Generate PDF Report")
            logger.info("=" * 70)

            top_score = session.query(ScoreRecord).filter(
                ScoreRecord.basin_id == basin_id
            ).order_by(ScoreRecord.final_score.desc()).first()

            if top_score:
                explainer = ExplainabilityEngine()
                explanation = explainer.explain_zone_score(
                    zone_id=top_score.grid_cell_id,
                    final_score=top_score.final_score,
                    final_rank=top_score.rank,
                    rule_components=top_score.components,
                    feature_dict={
                        "fault_density": top_score.rule_score,
                        "heat_flow_indicator": top_score.final_score,
                    },
                    confidence_score=top_score.confidence_score,
                    confidence_components={
                        "data_coverage": 0.80,
                        "data_quality": 0.75,
                        "missing_completeness": 0.85,
                    },
                    missing_data_count=0,
                    total_data_layers=8,
                )

                generator = PDFReportGenerator()

                # Convert FeatureAttribution objects to dictionaries
                top_features_dicts = [
                    {
                        "name": f.name,
                        "label": f.label,
                        "value": f.value,
                        "weight": f.weight,
                        "contribution": f.contribution,
                    }
                    for f in explanation.top_features
                ]

                pdf_bytes = generator.generate_report(
                    zone_name=f"Test Zone - {basin.name}",
                    basin_name=basin.name,
                    final_score=top_score.final_score,
                    final_rank=top_score.rank,
                    score_class=explanation.score_class,
                    score_components=explanation.score_components,
                    top_features=top_features_dicts,
                    missing_data_caveats=explanation.missing_data_caveats,
                    narrative_summary=explanation.narrative_summary,
                    recommended_actions=explanation.recommended_actions,
                    confidence_score=top_score.confidence_score,
                )

                report_path = TEST_DATA_DIR / "test_report_sqlite.pdf"
                with open(report_path, "wb") as f:
                    f.write(pdf_bytes)

                logger.info(f"✅ Generated PDF report: {report_path} ({len(pdf_bytes) / 1024:.1f} KB)")

            # Summary
            logger.info("")
            logger.info("=" * 70)
            logger.info("✅ FULL LOCAL PIPELINE TEST COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)
            logger.info(f"Basin ID: {basin_id}")
            logger.info(f"Grid Cells: {len(cells)}")
            logger.info(f"Database: {DB_PATH}")
            logger.info("")
            logger.info("Pipeline Summary:")
            logger.info("  ✓ Basin Creation: Complete")
            logger.info("  ✓ Grid Cell Generation: Complete")
            logger.info("  ✓ Feature Computation: Complete")
            logger.info("  ✓ Ensemble Scoring: Complete")
            logger.info("  ✓ PDF Report Generation: Complete")
            logger.info("")
            logger.info("Next Steps:")
            logger.info("  1. Review test output and database state")
            logger.info("  2. Start local PostgreSQL: docker-compose up -d db")
            logger.info("  3. Run full pipeline with database: python scripts/local_pipeline_test.py")
            logger.info("  4. Deploy Prefect: python -m prefect deployment build backend/workflows/data_pipeline.py")
            logger.info("  5. Deploy to GCP: terraform apply -f infra/terraform/")
            logger.info("")

            return 0

    except Exception as e:
        logger.error(f"❌ Pipeline test failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(test_full_pipeline())
