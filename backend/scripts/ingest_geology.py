#!/usr/bin/env python3
"""
Ingest geologic units from Macrostrat API into PostgreSQL.
Source: https://macrostrat.org/api/v2

Usage:
    python scripts/ingest_geology.py <basin_id> <west> <south> <east> <north>
"""

import sys
import argparse
import logging
from pathlib import Path
import requests
import geopandas as gpd
from shapely.geometry import shape
import json

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

MACROSTRAT_API = "https://macrostrat.org/api/v2"


def fetch_geology_from_macrostrat(bbox: tuple, limit: int = 1000) -> list:
    """
    Fetch geologic units from Macrostrat API.

    Args:
        bbox: (west, south, east, north)
        limit: Max features to fetch

    Returns:
        List of geologic units as GeoJSON features
    """
    west, south, east, north = bbox
    url = f"{MACROSTRAT_API}/units"
    params = {
        "bbox": f"{west},{south},{east},{north}",
        "limit": limit,
        "format": "geojson"
    }

    logger.info(f"Fetching geology from Macrostrat: {url}")
    response = requests.get(url, params=params, timeout=30)

    if response.status_code != 200:
        logger.error(f"Macrostrat API error: {response.status_code}")
        return []

    data = response.json()
    features = data.get("features", [])
    logger.info(f"Fetched {len(features)} geologic features")

    return features


def ingest_geology(basin_id: str, bbox: tuple, table_name: str = "geologic_units"):
    """
    Load geologic units from Macrostrat into PostgreSQL.

    Args:
        basin_id: Basin UUID
        bbox: (west, south, east, north)
        table_name: Target table name
    """
    engine = create_engine(settings.database_url, echo=False)

    try:
        # Fetch data from API
        features = fetch_geology_from_macrostrat(bbox)

        if not features:
            logger.warning("No geology features found")
            return False

        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")

        logger.info(f"Loaded {len(gdf)} geologic units")

        with Session(engine) as db:
            basin = db.query(BasinORM).filter(BasinORM.id == basin_id).first()
            if not basin:
                logger.error(f"Basin {basin_id} not found")
                return False

            logger.info(f"Writing to table '{table_name}' for basin {basin.name}")

            # Prepare GeoDataFrame
            gdf_clean = gdf[['geometry']].copy()

            # Add relevant columns if they exist
            for col in ['name', 'age', 'lithology', 'description', 'unit_id']:
                if col in gdf.columns:
                    gdf_clean[col] = gdf[col]

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

            # Create spatial index
            with engine.connect() as conn:
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table_name}_geom ON {table_name} USING GIST(geometry)"
                )
                conn.commit()
                logger.info(f"Created spatial index on {table_name}.geometry")

            # Log metadata
            data_layer = DataLayersORM(
                basin_id=basin_id,
                name="Macrostrat Geologic Units",
                source_name="Macrostrat Database",
                source_url="https://macrostrat.org/api/v2",
                layer_type="vector",
                target_table=table_name,
                license="CC-BY-4.0",
                resolution="Variable (depends on source geologic maps)",
                acquisition_date=datetime.utcnow(),
                source_confidence=0.75,
                data_quality=0.70,
                metadata={
                    "feature_count": len(gdf),
                    "crs": "EPSG:4326",
                    "bbox": list(bbox),
                    "api": "Macrostrat v2"
                }
            )
            db.add(data_layer)
            db.commit()

            logger.info(f"✅ Successfully ingested {len(gdf)} geologic units")
            return True

    except Exception as e:
        logger.error(f"Error ingesting geology data: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Macrostrat geology data into PostgreSQL"
    )
    parser.add_argument("basin_id", help="Basin UUID")
    parser.add_argument("west", type=float, help="Bounding box west longitude")
    parser.add_argument("south", type=float, help="Bounding box south latitude")
    parser.add_argument("east", type=float, help="Bounding box east longitude")
    parser.add_argument("north", type=float, help="Bounding box north latitude")
    parser.add_argument("--table", default="geologic_units", help="Target table name")

    args = parser.parse_args()
    bbox = (args.west, args.south, args.east, args.north)

    logger.info("Starting geology data ingestion...")
    success = ingest_geology(args.basin_id, bbox, args.table)

    if success:
        logger.info("✅ Geology ingestion completed successfully")
        return 0
    else:
        logger.error("❌ Geology ingestion failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
