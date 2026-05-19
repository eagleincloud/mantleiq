#!/usr/bin/env python3
"""
Ingest USGS fault line data into PostgreSQL.
Source: https://www.usgs.gov/programs/earthquake-hazards/faults

Usage:
    python scripts/ingest_faults.py <shapefile_path> <basin_id>
"""

import sys
import argparse
import logging
from pathlib import Path
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.orm import BasinORM, DataLayersORM
from geoalchemy2 import Geometry
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def ingest_faults(shapefile_path: str, basin_id: str, table_name: str = "faults"):
    """
    Load fault lines from shapefile into PostgreSQL.

    Args:
        shapefile_path: Path to USGS fault shapefile
        basin_id: Basin UUID to associate faults with
        table_name: Target table name in database
    """
    engine = create_engine(settings.database_url, echo=False)

    try:
        # Read shapefile
        logger.info(f"Reading shapefile: {shapefile_path}")
        gdf = gpd.read_file(shapefile_path)

        if gdf.crs != "EPSG:4326":
            logger.info(f"Reprojecting from {gdf.crs} to EPSG:4326")
            gdf = gdf.to_crs("EPSG:4326")

        logger.info(f"Loaded {len(gdf)} fault features")

        # Verify basin exists
        with Session(engine) as db:
            basin = db.query(BasinORM).filter(BasinORM.id == basin_id).first()
            if not basin:
                logger.error(f"Basin {basin_id} not found")
                return False

            logger.info(f"Writing to table '{table_name}' for basin {basin.name}")

            # Write to database using SQLAlchemy
            gdf.to_postgis(
                table_name,
                engine,
                schema=None,
                if_exists="replace",
                index=False,
                chunksize=100,
                method="multi"
            )

            # Create indexes
            with engine.connect() as conn:
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_geom ON {table_name} USING GIST(geometry)"
                )
                conn.commit()
                logger.info(f"Created spatial index on {table_name}.geometry")

            # Log data layer metadata
            data_layer = DataLayersORM(
                basin_id=basin_id,
                name="USGS Fault Lines",
                source_name="USGS Earthquake Hazards",
                source_url="https://www.usgs.gov/programs/earthquake-hazards/faults",
                layer_type="vector",
                curated_uri=shapefile_path,
                target_table=table_name,
                license="Public Domain",
                resolution="Varies by source (1:24k to 1:100k)",
                acquisition_date=datetime.utcnow(),
                source_confidence=0.9,
                data_quality=0.85,
                metadata={
                    "feature_count": len(gdf),
                    "crs": "EPSG:4326",
                    "geometry_type": gdf.geometry.type.unique().tolist()
                }
            )
            db.add(data_layer)
            db.commit()

            logger.info(f"✅ Successfully ingested {len(gdf)} fault lines")
            return True

    except Exception as e:
        logger.error(f"Error ingesting faults: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Ingest USGS fault data into PostgreSQL"
    )
    parser.add_argument(
        "shapefile_path",
        help="Path to USGS fault shapefile"
    )
    parser.add_argument(
        "basin_id",
        help="Basin UUID"
    )
    parser.add_argument(
        "--table",
        default="faults",
        help="Target table name (default: faults)"
    )

    args = parser.parse_args()

    logger.info("Starting fault data ingestion...")
    success = ingest_faults(args.shapefile_path, args.basin_id, args.table)

    if success:
        logger.info("✅ Fault ingestion completed successfully")
        return 0
    else:
        logger.error("❌ Fault ingestion failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
