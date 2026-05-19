#!/usr/bin/env python3
"""
Ingest IHFC Global Heat Flow Database into PostgreSQL.
Source: https://www.ihfc-iugg.org/products/global-heat-flow-database/

Usage:
    python scripts/ingest_heatflow.py <csv_path> <basin_id>
"""

import sys
import argparse
import logging
from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.orm import BasinORM, DataLayersORM
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def ingest_heatflow(csv_path: str, basin_id: str, table_name: str = "heatflow_points"):
    """
    Load heat flow points from CSV into PostgreSQL.

    Args:
        csv_path: Path to IHFC heat flow CSV
        basin_id: Basin UUID to associate points with
        table_name: Target table name

    CSV expected columns:
        - latitude, longitude (or lat, lon)
        - heat_flow (in mW/m²)
        - name (optional)
        - reference (optional)
    """
    engine = create_engine(settings.database_url, echo=False)

    try:
        # Read CSV
        logger.info(f"Reading CSV: {csv_path}")
        df = pd.read_csv(csv_path)

        # Normalize column names
        df.columns = [col.lower().strip() for col in df.columns]

        # Find lat/lon columns
        lat_col = next((c for c in df.columns if c in ['latitude', 'lat', 'y']), None)
        lon_col = next((c for c in df.columns if c in ['longitude', 'lon', 'x']), None)

        if not lat_col or not lon_col:
            logger.error(f"CSV must contain latitude/longitude columns")
            return False

        # Create geometry
        geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

        logger.info(f"Loaded {len(gdf)} heat flow points")

        with Session(engine) as db:
            basin = db.query(BasinORM).filter(BasinORM.id == basin_id).first()
            if not basin:
                logger.error(f"Basin {basin_id} not found")
                return False

            logger.info(f"Writing to table '{table_name}' for basin {basin.name}")

            # Prepare data
            gdf_clean = gdf[['geometry']].copy()

            # Add heat flow column if exists
            if 'heat_flow' in df.columns or 'mw_m2' in df.columns:
                heat_col = next((c for c in df.columns if c in ['heat_flow', 'mw_m2', 'heat_flow_mw_m2']), None)
                if heat_col:
                    gdf_clean['mw_m2'] = df[heat_col].astype(float)

            # Add other columns
            for col in ['name', 'reference', 'latitude', 'longitude']:
                if col in df.columns:
                    gdf_clean[col] = df[col]

            # Write to database
            gdf_clean.to_postgis(
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
                if 'mw_m2' in gdf_clean.columns:
                    conn.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_mw ON {table_name}(mw_m2)"
                    )
                conn.commit()
                logger.info(f"Created spatial and attribute indexes on {table_name}")

            # Log metadata
            data_layer = DataLayersORM(
                basin_id=basin_id,
                name="IHFC Global Heat Flow Database",
                source_name="International Heat Flow Commission",
                source_url="https://www.ihfc-iugg.org/products/global-heat-flow-database/",
                layer_type="point",
                curated_uri=csv_path,
                target_table=table_name,
                license="Public Domain",
                resolution="Point measurements",
                acquisition_date=datetime.utcnow(),
                source_confidence=0.85,
                data_quality=0.80,
                metadata={
                    "point_count": len(gdf),
                    "crs": "EPSG:4326",
                    "units": "mW/m²"
                }
            )
            db.add(data_layer)
            db.commit()

            logger.info(f"✅ Successfully ingested {len(gdf)} heat flow points")
            return True

    except Exception as e:
        logger.error(f"Error ingesting heat flow data: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Ingest IHFC heat flow data into PostgreSQL"
    )
    parser.add_argument(
        "csv_path",
        help="Path to IHFC heat flow CSV file"
    )
    parser.add_argument(
        "basin_id",
        help="Basin UUID"
    )
    parser.add_argument(
        "--table",
        default="heatflow_points",
        help="Target table name (default: heatflow_points)"
    )

    args = parser.parse_args()

    logger.info("Starting heat flow data ingestion...")
    success = ingest_heatflow(args.csv_path, args.basin_id, args.table)

    if success:
        logger.info("✅ Heat flow ingestion completed successfully")
        return 0
    else:
        logger.error("❌ Heat flow ingestion failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
