#!/usr/bin/env python3
"""
Local Manual Prefect Pipeline - Single Execution
================================================

Run the complete MantleIQ pipeline locally without scheduling.
Uses SQLite for database operations.
Designed for manual triggering: "run it", "run again", etc.

Usage:
    python workflows/local_manual_pipeline.py <basin_id>
    python workflows/local_manual_pipeline.py kansas_rift_2024
"""

import sys
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from prefect import flow, task, get_run_logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.feature_engineering import FeatureComputer
from app.services.scoring.rule_scorer import RuleScorer, FeatureScores
from app.services.scoring.ensemble import EnsembleScorer
from app.services.explainability import ExplainabilityEngine
from app.services.export import PDFReportGenerator

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Database configuration
LOCAL_STORAGE = Path("/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/local_storage")
DB_PATH = LOCAL_STORAGE / "databases" / "mantleiq_pipeline.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Ensure directories exist
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
(LOCAL_STORAGE / "outputs").mkdir(parents=True, exist_ok=True)
(LOCAL_STORAGE / "reports").mkdir(parents=True, exist_ok=True)
(LOCAL_STORAGE / "logs").mkdir(parents=True, exist_ok=True)

# Simplified ORM for local testing
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BasinRecord(Base):
    """Test basin record"""
    __tablename__ = "basins"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    region = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GridCellRecord(Base):
    """Test grid cell record"""
    __tablename__ = "grid_cells"
    id = Column(String, primary_key=True)
    basin_id = Column(String, nullable=False)
    grid_index = Column(Integer, nullable=True)
    centroid_lon = Column(Float, nullable=True)
    centroid_lat = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FeatureRecord(Base):
    """Test feature record"""
    __tablename__ = "features"
    id = Column(String, primary_key=True)
    grid_cell_id = Column(String, nullable=False)
    basin_id = Column(String, nullable=False)
    fault_density = Column(Float, nullable=True)
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
    id = Column(String, primary_key=True)
    grid_cell_id = Column(String, nullable=False)
    basin_id = Column(String, nullable=False)
    rule_score = Column(Float, nullable=True)
    ensemble_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    components = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# PREFECT TASKS
# ============================================================================

@task(name="create_basin", retries=2)
def create_basin(basin_name: str, region: str = "USA") -> str:
    """Create or retrieve basin record."""
    logger = get_run_logger()
    logger.info(f"Creating basin: {basin_name}")

    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        basin = BasinRecord(
            id=str(uuid.uuid4()),
            name=basin_name,
            region=region,
        )
        session.add(basin)
        session.commit()
        session.refresh(basin)
        logger.info(f"✅ Basin created: {basin.id}")
        return basin.id


@task(name="create_grid", retries=2)
def create_grid(basin_id: str, cell_count: int = 10) -> list:
    """Create grid cells."""
    logger = get_run_logger()
    logger.info(f"Creating {cell_count} grid cells")

    engine = create_engine(DATABASE_URL, echo=False)

    with Session(engine) as session:
        cells = []
        for i in range(cell_count):
            lon = -95.0 + (i % 5) * 0.5
            lat = 38.0 + (i // 5) * 0.5

            cell = GridCellRecord(
                id=str(uuid.uuid4()),
                basin_id=basin_id,
                grid_index=i,
                centroid_lon=lon,
                centroid_lat=lat,
            )
            session.add(cell)
            cells.append(cell.id)

        session.commit()
        logger.info(f"✅ Created {len(cells)} grid cells")
        return cells


@task(name="compute_features", retries=2)
def compute_features(basin_id: str, cell_ids: list) -> int:
    """Compute geospatial features for grid cells."""
    logger = get_run_logger()
    logger.info(f"Computing features for {len(cell_ids)} cells")

    engine = create_engine(DATABASE_URL, echo=False)
    computer = FeatureComputer()

    with Session(engine) as session:
        for idx, cell_id in enumerate(cell_ids, 1):
            features = computer.compute_cell_features(
                cell_id=cell_id,
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
                grid_cell_id=cell_id,
                basin_id=basin_id,
                fault_density=features.fault_density,
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
        logger.info(f"✅ Computed features for {len(cell_ids)} cells")
        return len(cell_ids)


@task(name="score_cells", retries=2)
def score_cells(basin_id: str, cell_ids: list) -> int:
    """Score grid cells using ensemble model."""
    logger = get_run_logger()
    logger.info(f"Scoring {len(cell_ids)} cells")

    engine = create_engine(DATABASE_URL, echo=False)

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

    with Session(engine) as session:
        scored = 0
        for cell_id in cell_ids:
            feature_record = session.query(FeatureRecord).filter(
                FeatureRecord.grid_cell_id == cell_id
            ).first()

            if not feature_record:
                continue

            feature_scores = FeatureScores(
                fault_intersection=feature_record.fault_density,
                ultramafic_proximity=0.7,
                gravity_anomaly=feature_record.gravity_anomaly,
                magnetic_anomaly=0.6,
                heat_flow_indicator=feature_record.heat_flow_indicator,
                structural_complexity=0.5,
                seep_proximity=0.5,
            )

            scores = ensemble_scorer.score(feature_scores)

            score_record = ScoreRecord(
                id=str(uuid.uuid4()),
                grid_cell_id=cell_id,
                basin_id=basin_id,
                rule_score=scores.rule_score,
                ensemble_score=scores.ensemble_score,
                final_score=scores.final_score,
                confidence_score=scores.confidence_adjusted,
                rank=scores.final_rank,
                components=scores.rule_components,
            )
            session.add(score_record)
            scored += 1

        session.commit()
        logger.info(f"✅ Scored {scored} cells")
        return scored


@task(name="generate_reports", retries=2)
def generate_reports(basin_id: str) -> str:
    """Generate PDF reports."""
    logger = get_run_logger()
    logger.info(f"Generating PDF reports")

    engine = create_engine(DATABASE_URL, echo=False)
    generator = PDFReportGenerator()
    explainer = ExplainabilityEngine()

    with Session(engine) as session:
        top_score = session.query(ScoreRecord).filter(
            ScoreRecord.basin_id == basin_id
        ).order_by(ScoreRecord.final_score.desc()).first()

        if not top_score:
            logger.warning("No scores found for report generation")
            return ""

        explanation = explainer.explain_zone_score(
            zone_id=top_score.grid_cell_id,
            final_score=top_score.final_score,
            final_rank=top_score.rank,
            rule_components=top_score.components,
            feature_dict={"fault_density": top_score.rule_score},
            confidence_score=top_score.confidence_score,
            confidence_components={
                "data_coverage": 0.80,
                "data_quality": 0.75,
                "missing_completeness": 0.85,
            },
            missing_data_count=0,
            total_data_layers=8,
        )

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
            zone_name=f"Top Prospect - Cell {top_score.grid_cell_id[:8]}",
            basin_name="Test Basin",
            final_score=top_score.final_score,
            final_rank=top_score.rank,
            score_class=explanation.score_class,
            score_components=top_score.components,
            top_features=top_features_dicts,
            missing_data_caveats=explanation.missing_data_caveats,
            narrative_summary=explanation.narrative_summary,
            recommended_actions=explanation.recommended_actions,
            confidence_score=top_score.confidence_score,
        )

        report_path = LOCAL_STORAGE / "reports" / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "wb") as f:
            f.write(pdf_bytes)

        logger.info(f"✅ Generated report: {report_path} ({len(pdf_bytes) / 1024:.2f} KB)")
        return str(report_path)


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

@flow(
    name="mantleiq-local-manual-pipeline",
    description="Local manual MantleIQ pipeline execution (no scheduling)",
)
def local_manual_pipeline(
    basin_name: str = "Kansas Rift",
    region: str = "Kansas, USA",
    cell_count: int = 10,
) -> dict:
    """
    Execute complete MantleIQ pipeline locally.
    Manual execution only - no scheduling.

    Args:
        basin_name: Name of analysis basin
        region: Geographic region
        cell_count: Number of grid cells to analyze

    Returns:
        Pipeline execution summary
    """
    logger = get_run_logger()
    logger.info("")
    logger.info("=" * 80)
    logger.info("MANTLEIQ LOCAL MANUAL PIPELINE")
    logger.info("=" * 80)
    logger.info("")

    start_time = datetime.utcnow()

    try:
        # Step 1: Create Basin
        logger.info("STEP 1: Create Basin")
        logger.info("-" * 80)
        basin_id = create_basin(basin_name, region)

        # Step 2: Create Grid
        logger.info("\nSTEP 2: Create Grid Cells")
        logger.info("-" * 80)
        cell_ids = create_grid(basin_id, cell_count)

        # Step 3: Compute Features
        logger.info("\nSTEP 3: Compute Features")
        logger.info("-" * 80)
        features_count = compute_features(basin_id, cell_ids)

        # Step 4: Score Cells
        logger.info("\nSTEP 4: Score Cells")
        logger.info("-" * 80)
        scored_count = score_cells(basin_id, cell_ids)

        # Step 5: Generate Reports
        logger.info("\nSTEP 5: Generate Reports")
        logger.info("-" * 80)
        report_path = generate_reports(basin_id)

        # Summary
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"Basin ID:              {basin_id}")
        logger.info(f"Grid Cells:            {len(cell_ids)}")
        logger.info(f"Features Computed:     {features_count}")
        logger.info(f"Cells Scored:          {scored_count}")
        logger.info(f"Reports Generated:     {report_path}")
        logger.info(f"Execution Time:        {elapsed:.2f} seconds")
        logger.info("")

        return {
            "status": "success",
            "basin_id": basin_id,
            "cells_processed": len(cell_ids),
            "features_computed": features_count,
            "cells_scored": scored_count,
            "report_path": report_path,
            "execution_time_seconds": elapsed,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("")
        logger.error("=" * 80)
        logger.error(f"❌ PIPELINE EXECUTION FAILED: {e}")
        logger.error("=" * 80)
        logger.error("")
        raise


if __name__ == "__main__":
    # Manual execution entry point
    basin_name = sys.argv[1] if len(sys.argv) > 1 else "Kansas Rift"
    result = local_manual_pipeline(basin_name=basin_name, cell_count=10)
    print("\n" + "=" * 80)
    print("EXECUTION RESULT")
    print("=" * 80)
    for key, value in result.items():
        print(f"{key:30} {value}")
    print("=" * 80)
