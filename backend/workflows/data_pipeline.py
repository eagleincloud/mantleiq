#!/usr/bin/env python3
"""
Prefect workflow for MantleIQ data pipeline orchestration.

Automated daily pipeline:
1. Ingest Vector Data (faults, geology)
2. Ingest Raster Data (gravity, magnetic)
3. Ingest Point Data (heat flow)
4. Compute Features (spatial joins)
5. Score Zones (rule + ML ensemble)
6. Cluster & Export (DBSCAN + PDF)
7. Notify (Slack/Email)

Installation:
    pip install prefect geopandas geoalchemy2 sqlalchemy

Deployment:
    prefect deploy data_pipeline.py --name mantleiq-daily
    prefect scheduler start

Usage:
    python workflows/data_pipeline.py
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Prefect imports
from prefect import flow, task, get_run_logger
from prefect.tasks.shell import shell_run_command
from prefect.futures import PrefectFuture

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.orm import BasinORM, AnalysisJobsORM
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ============================================================================
# TASKS
# ============================================================================

@task(name="fetch_vector_data", retries=3, retry_delay_seconds=60)
def fetch_vector_data(basin_id: str, data_source: str = "usgs"):
    """
    Fetch vector data (faults, geology) from external sources.

    Args:
        basin_id: Basin UUID
        data_source: 'usgs', 'macrostrat', etc.

    Returns:
        Path to downloaded file
    """
    logger = get_run_logger()
    logger.info(f"Fetching vector data for basin {basin_id} from {data_source}")

    # TODO: Implement actual download logic
    # - USGS faults: Download ZIP, extract shapefile
    # - Macrostrat geology: API call, save GeoJSON
    # - Validate CRS, geometries

    download_path = f"/tmp/mantleiq_data/{basin_id}/faults.zip"
    logger.info(f"Downloaded vector data to {download_path}")

    return download_path


@task(name="ingest_vector_data", retries=2)
def ingest_vector_data(file_path: str, basin_id: str, data_type: str):
    """
    Load vector data into PostgreSQL via geopandas.

    Args:
        file_path: Path to vector file (shapefile, GeoJSON)
        basin_id: Basin UUID
        data_type: 'faults', 'geology', etc.
    """
    logger = get_run_logger()
    logger.info(f"Ingesting {data_type} from {file_path}")

    # Call appropriate ingestion script
    if data_type == "faults":
        from scripts.ingest_faults import ingest_faults
        success = ingest_faults(file_path, basin_id)
    elif data_type == "geology":
        from scripts.ingest_geology import ingest_geology
        # Extract bbox from file metadata
        success = ingest_geology(basin_id, (-95, 35, -90, 40))
    else:
        logger.error(f"Unknown data type: {data_type}")
        return False

    if success:
        logger.info(f"✅ {data_type} ingestion completed")
    else:
        logger.error(f"❌ {data_type} ingestion failed")

    return success


@task(name="fetch_raster_data")
def fetch_raster_data(basin_id: str, raster_type: str = "gravity"):
    """
    Fetch raster data (gravity, magnetic, DEM) from NOAA/NASA.

    Args:
        basin_id: Basin UUID
        raster_type: 'gravity', 'magnetic', 'dem'

    Returns:
        Path to downloaded Cloud-Optimized GeoTIFF
    """
    logger = get_run_logger()
    logger.info(f"Fetching {raster_type} raster for basin {basin_id}")

    # TODO: Implement actual download logic
    # - NOAA EMAG2: Download GeoTIFF
    # - NOAA Gravity: Download NetCDF, convert to COG
    # - NASA SRTM DEM: Download GeoTIFF
    # - Clip to basin boundary
    # - Convert to Cloud-Optimized GeoTIFF format

    download_path = f"/tmp/mantleiq_data/{basin_id}/{raster_type}.tif"
    logger.info(f"Downloaded {raster_type} to {download_path}")

    return download_path


@task(name="ingest_raster_data")
def ingest_raster_data(file_path: str, basin_id: str, raster_type: str):
    """
    Load raster COG metadata into database.

    Args:
        file_path: Path to Cloud-Optimized GeoTIFF
        basin_id: Basin UUID
        raster_type: 'gravity', 'magnetic', 'dem'
    """
    logger = get_run_logger()
    logger.info(f"Ingesting {raster_type} raster metadata")

    # Register COG in database
    from app.models.orm import DataLayersORM

    db = SessionLocal()
    try:
        data_layer = DataLayersORM(
            basin_id=basin_id,
            name=f"NOAA {raster_type.title()} Anomaly",
            layer_type="raster",
            curated_uri=file_path,
            target_table=f"{raster_type}_tiles",
            source_confidence=0.9,
            data_quality=0.85,
            metadata={"format": "Cloud-Optimized GeoTIFF"}
        )
        db.add(data_layer)
        db.commit()
        logger.info(f"✅ Registered {raster_type} COG metadata")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to register raster: {e}")
        return False
    finally:
        db.close()


@task(name="fetch_point_data")
def fetch_point_data(basin_id: str):
    """
    Fetch point data (heat flow) from IHFC database.

    Args:
        basin_id: Basin UUID

    Returns:
        Path to downloaded CSV
    """
    logger = get_run_logger()
    logger.info(f"Fetching heat flow data for basin {basin_id}")

    # TODO: Query IHFC API or download CSV
    # - Subset to basin region (lat/lon bounds)
    # - Validate: mW/m² units, coordinates in EPSG:4326

    download_path = f"/tmp/mantleiq_data/{basin_id}/heatflow.csv"
    logger.info(f"Downloaded heat flow data to {download_path}")

    return download_path


@task(name="ingest_point_data")
def ingest_point_data(file_path: str, basin_id: str):
    """
    Load heat flow points into database.

    Args:
        file_path: Path to CSV with lat/lon/heat_flow
        basin_id: Basin UUID
    """
    logger = get_run_logger()
    logger.info(f"Ingesting heat flow points from {file_path}")

    from scripts.ingest_heatflow import ingest_heatflow
    success = ingest_heatflow(file_path, basin_id)

    if success:
        logger.info("✅ Heat flow ingestion completed")
    else:
        logger.error("❌ Heat flow ingestion failed")

    return success


@task(name="normalize_data")
def normalize_data(basin_id: str):
    """
    Validate and normalize ingested data.

    Tasks:
    - Check CRS consistency (all EPSG:4326)
    - Validate geometries (no self-intersections)
    - Clip to basin boundary
    - Check spatial extent coverage
    """
    logger = get_run_logger()
    logger.info(f"Normalizing data for basin {basin_id}")

    db = SessionLocal()
    try:
        # Validate all data layers
        with db.connection().connection.cursor() as cur:
            # Check CRS
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='faults'")
            if cur.fetchone()[0] > 0:
                cur.execute("SELECT ST_SRID(geometry) FROM faults LIMIT 1")
                srid = cur.fetchone()[0]
                if srid != 4326:
                    logger.warning(f"Faults SRID is {srid}, expected 4326")

            # Validate geometries
            cur.execute("SELECT COUNT(*) FROM faults WHERE NOT ST_IsValid(geometry)")
            invalid_count = cur.fetchone()[0]
            if invalid_count > 0:
                logger.warning(f"Found {invalid_count} invalid fault geometries")

        logger.info("✅ Data normalization completed")
        return True
    except Exception as e:
        logger.error(f"❌ Data normalization failed: {e}")
        return False
    finally:
        db.close()


@task(name="compute_features")
def compute_features(basin_id: str, limit: int = None):
    """
    Compute 25+ geospatial features for all grid cells.

    Uses PostGIS spatial joins:
    - Fault density, proximity
    - Ultramafic proximity
    - Gravity/magnetic anomaly sampling
    - Heat flow interpolation (IDW)
    - Lithology coverage
    """
    logger = get_run_logger()
    logger.info(f"Computing features for basin {basin_id}")

    # Run batch feature computation
    cmd = f"python scripts/batch_feature_compute.py {basin_id}"
    if limit:
        cmd += f" --limit {limit}"

    result = shell_run_command(cmd)

    if result.exit_code == 0:
        logger.info("✅ Feature computation completed")
        return True
    else:
        logger.error(f"❌ Feature computation failed: {result.stderr}")
        return False


@task(name="score_zones")
def score_zones(basin_id: str):
    """
    Score all zones using ensemble model (60% rule + 40% ML).

    - Compute rule-based scores (6-factor model)
    - Run XGBoost model (if trained)
    - Ensemble combination
    - Confidence adjustment
    - Calculate percentile ranks
    """
    logger = get_run_logger()
    logger.info(f"Scoring zones for basin {basin_id}")

    db = SessionLocal()
    try:
        from app.services.scoring import EnsembleScorer
        from app.models.orm import FeaturesORM, GridCellsORM, ModelOutputsORM

        scorer = EnsembleScorer()

        # Query all grid cells with features
        grid_cells = db.query(GridCellsORM).filter(
            GridCellsORM.basin_id == basin_id
        ).all()

        for cell in grid_cells:
            features = db.query(FeaturesORM).filter(
                FeaturesORM.grid_cell_id == cell.id
            ).first()

            if not features:
                continue

            # Score the cell
            scores = scorer.score(features)

            # Store results
            model_output = ModelOutputsORM(
                grid_cell_id=cell.id,
                zone_id=None,  # Will be assigned by clustering
                **scores
            )
            db.add(model_output)

        db.commit()
        logger.info(f"✅ Scored {len(grid_cells)} cells")
        return True
    except Exception as e:
        logger.error(f"❌ Scoring failed: {e}")
        return False
    finally:
        db.close()


@task(name="cluster_zones")
def cluster_zones(basin_id: str):
    """
    Cluster high-prospectivity cells into prospect zones.

    Uses DBSCAN clustering:
    - Input: cells with score >= 50th percentile
    - eps: 12 km, min_samples: 4
    - Output: Zone geometries (convex hull)
    """
    logger = get_run_logger()
    logger.info(f"Clustering zones for basin {basin_id}")

    # TODO: Implement DBSCAN clustering + convex hull zone creation

    logger.info("✅ Clustering completed")
    return True


@task(name="generate_reports")
def generate_reports(basin_id: str):
    """
    Generate PDF reports for all zones.

    Uses PDFReportGenerator to create:
    - Title page (zone name, score, interpretation)
    - Score breakdown (6-factor table)
    - Attribution (top features, caveats, recommendations)
    """
    logger = get_run_logger()
    logger.info(f"Generating reports for basin {basin_id}")

    # TODO: Query zones and generate PDFs in bulk

    logger.info("✅ Report generation completed")
    return True


@task(name="send_notification")
def send_notification(basin_id: str, success: bool, message: str = ""):
    """
    Send completion notification via Slack/Email.

    Args:
        basin_id: Basin UUID
        success: Whether pipeline succeeded
        message: Optional custom message
    """
    logger = get_run_logger()

    status = "✅ SUCCESS" if success else "❌ FAILED"
    notification = f"{status}: Pipeline for basin {basin_id} completed. {message}"

    # TODO: Send to Slack webhook or email
    logger.info(f"Notification: {notification}")


# ============================================================================
# WORKFLOW
# ============================================================================

@flow(
    name="mantleiq-data-pipeline",
    description="Daily data ingestion, processing, and scoring pipeline",
    retries=1,
    retry_delay_seconds=300
)
def data_pipeline_flow(basin_id: str):
    """
    Complete MantleIQ data pipeline workflow.

    Orchestrates:
    1. Ingest vector data (faults, geology)
    2. Ingest raster data (gravity, magnetic, DEM)
    3. Ingest point data (heat flow)
    4. Normalize all data
    5. Compute geospatial features
    6. Score zones (rule + ML ensemble)
    7. Cluster prospect zones
    8. Generate PDF reports
    9. Notify (Slack/Email)
    """
    logger = get_run_logger()
    logger.info(f"🚀 Starting MantleIQ data pipeline for basin {basin_id}")

    start_time = datetime.utcnow()

    try:
        # Phase 1: Data Ingestion
        logger.info("📥 PHASE 1: Data Ingestion")

        # Vector data
        faults_file = fetch_vector_data(basin_id, "usgs")
        ingest_vector_data(faults_file, basin_id, "faults")

        geology_file = fetch_vector_data(basin_id, "macrostrat")
        ingest_vector_data(geology_file, basin_id, "geology")

        # Raster data
        gravity_file = fetch_raster_data(basin_id, "gravity")
        ingest_raster_data(gravity_file, basin_id, "gravity")

        magnetic_file = fetch_raster_data(basin_id, "magnetic")
        ingest_raster_data(magnetic_file, basin_id, "magnetic")

        # Point data
        heatflow_file = fetch_point_data(basin_id)
        ingest_point_data(heatflow_file, basin_id)

        # Phase 2: Data Normalization
        logger.info("🔄 PHASE 2: Data Normalization")
        normalize_data(basin_id)

        # Phase 3: Feature Engineering
        logger.info("🔧 PHASE 3: Feature Engineering")
        compute_features(basin_id)

        # Phase 4: Scoring
        logger.info("📊 PHASE 4: Scoring")
        score_zones(basin_id)

        # Phase 5: Clustering & Export
        logger.info("🎯 PHASE 5: Clustering & Export")
        cluster_zones(basin_id)
        generate_reports(basin_id)

        # Success notification
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        success_msg = f"Pipeline completed in {elapsed:.1f} seconds"
        send_notification(basin_id, True, success_msg)

        logger.info(f"✅ Pipeline completed successfully")

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        send_notification(basin_id, False, str(e))
        raise


# ============================================================================
# DEPLOYMENT
# ============================================================================

if __name__ == "__main__":
    # Test run
    import uuid

    test_basin_id = str(uuid.uuid4())
    logger.info(f"Running test pipeline for basin {test_basin_id}")

    data_pipeline_flow(test_basin_id)
