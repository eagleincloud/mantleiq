#!/usr/bin/env python3
'''
Import downloaded geospatial datasets into Supabase PostgreSQL
'''

import geopandas as gpd
from sqlalchemy import create_engine
from urllib.parse import quote
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql+psycopg2://postgres:417BajrangNagar%401@db.ttimdqokzalxluwmezcz.supabase.co:5432/postgres"
DATA_DIR = Path("/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/local_storage/datasets")

def import_geojson_to_supabase(geojson_file, table_name):
    """Import GeoJSON file to Supabase PostGIS table"""
    logger.info(f"Importing {geojson_file} -> {table_name}...")

    try:
        gdf = gpd.read_file(geojson_file)
        engine = create_engine(DATABASE_URL)

        gdf.to_postgis(
            table_name,
            engine,
            if_exists='replace',
            index=True,
            chunksize=1000
        )

        logger.info(f"✅ Imported {len(gdf)} features to {table_name}")
        return True
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    # Import geological units
    import_geojson_to_supabase(
        DATA_DIR / "macrostrat_geology.geojson",
        "geologic_units"
    )

    # Import faults (if available)
    import_geojson_to_supabase(
        DATA_DIR / "usgs_faults.geojson",
        "faults"
    )

    logger.info("\n✅ All datasets imported to Supabase!")
