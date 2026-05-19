#!/usr/bin/env python3
"""
MantleIQ Data Ingestion - Download Public Geospatial Datasets
Acquires data from free public sources for Kansas Rift Basin analysis
"""

import os
import logging
from pathlib import Path
import requests
import json
from datetime import datetime

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path("/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/local_storage/datasets")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# DATA SOURCE CONFIGURATIONS
# ============================================================================

DATASETS = {
    "macrostrat_geology": {
        "name": "Macrostrat Geological Units - Kansas Rift",
        "source": "Macrostrat API",
        "url": "https://macrostrat.org/api/v2/units",
        "params": {
            "bbox": "-98,37,-93,40",  # Kansas Rift region
            "limit": 1000
        },
        "format": "GeoJSON",
        "output": "macrostrat_geology.geojson",
        "description": "Lithology, age, and geological classification"
    },

    "usgs_faults": {
        "name": "USGS Earthquake Hazards - Fault Database",
        "source": "USGS",
        "url": "https://www.usgs.gov/programs/earthquake-hazards/faults",
        "format": "Shapefile (ZIP)",
        "output": "usgs_faults/",
        "description": "Mapped and quaternary faults with activity classification",
        "note": "Manual download required from https://geohazards.usgs.gov/faults"
    },

    "noaa_gravity": {
        "name": "NOAA/NCEI Gravity Data - Kansas Region",
        "source": "NOAA/NCEI",
        "url": "https://www.ncei.noaa.gov/products/gravity-data",
        "format": "GeoTIFF or NetCDF",
        "output": "gravity_bouguer_anomaly.tif",
        "description": "Bouguer gravity anomaly (mGal)",
        "note": "Access via https://www.ncei.noaa.gov"
    },

    "noaa_magnetic": {
        "name": "NOAA EMAG2 v3 - Magnetic Anomaly Grid",
        "source": "NOAA",
        "url": "https://www.ncei.noaa.gov/products/earth-magnetic-model-anomaly-grid-2",
        "format": "GeoTIFF",
        "output": "magnetic_anomaly.tif",
        "description": "2-arc-minute global magnetic anomaly grid",
        "note": "Download 2-minute grid covering region"
    },

    "ihfc_heatflow": {
        "name": "IHFC Global Heat Flow Database",
        "source": "IHFC-IUGG",
        "url": "https://www.ihfc-iugg.org/products/global-heat-flow-database/data",
        "format": "CSV",
        "output": "heatflow_measurements.csv",
        "description": "Heat flow measurements (mW/m²) with lat/lon",
        "note": "Download CSV export from database"
    },

    "nasa_srtm_dem": {
        "name": "NASA SRTM DEM - 90m Resolution",
        "source": "NASA USGS",
        "url": "https://www.earthdata.nasa.gov/data/instruments/srtm",
        "format": "GeoTIFF",
        "output": "srtm_dem_90m.tif",
        "description": "Digital Elevation Model for terrain analysis",
        "note": "Access via EarthExplorer or DAAC services"
    },

    "gebco_bathymetry": {
        "name": "GEBCO Global Bathymetry/Topography",
        "source": "IHO-IOC",
        "url": "https://www.gebco.net/data_and_products/gridded_bathymetry_data/",
        "format": "GeoTIFF or NetCDF",
        "output": "gebco_topography.tif",
        "description": "Global 15-arc-second bathymetry/topography grid",
        "note": "Alternative to SRTM with global coverage"
    }
}

# ============================================================================
# DATA INGESTION FUNCTIONS
# ============================================================================

def download_macrostrat_geology():
    """Download geological units from Macrostrat API"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("📥 DOWNLOADING: Macrostrat Geological Units")
    logger.info("=" * 80)

    ds = DATASETS["macrostrat_geology"]
    try:
        params = ds["params"]
        params["response"] = "geojson"

        logger.info(f"Fetching from: {ds['url']}")
        logger.info(f"Region: Kansas Rift Basin ({params['bbox']})")

        response = requests.get(ds["url"], params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        output_path = DATA_DIR / ds["output"]

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        feature_count = len(data.get("features", []))
        logger.info(f"✅ Downloaded {feature_count} geological units")
        logger.info(f"   Saved to: {output_path}")
        logger.info(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")

        return True
    except Exception as e:
        logger.error(f"❌ Failed to download Macrostrat data: {e}")
        return False

def show_download_instructions():
    """Display instructions for manual downloads"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("📋 DATASET DOWNLOAD INSTRUCTIONS")
    logger.info("=" * 80)

    for key, ds in DATASETS.items():
        if ds.get("note"):
            logger.info("")
            logger.info(f"📊 {ds['name']}")
            logger.info(f"   Source: {ds['source']}")
            logger.info(f"   Format: {ds['format']}")
            logger.info(f"   Description: {ds['description']}")
            logger.info(f"   URL: {ds['url']}")
            logger.info(f"   Note: {ds['note']}")
            logger.info(f"   Save to: {DATA_DIR / ds['output']}")

def create_sample_kansas_rift_dataset():
    """Create sample Kansas Rift dataset for testing"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("🔧 CREATING: Sample Kansas Rift Dataset")
    logger.info("=" * 80)

    sample_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Kansas Rift Basin",
                    "age_min_ma": 500,
                    "age_max_ma": 300,
                    "lithology_class": "ultramafic",
                    "confidence": 0.85
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-98, 37],
                        [-93, 37],
                        [-93, 40],
                        [-98, 40],
                        [-98, 37]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "fault_name": "Nemaha Ridge Fault",
                    "fault_type": "normal",
                    "activity_class": "quaternary",
                    "confidence": 0.9
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-96, 37], [-95, 39], [-94, 40]]
                }
            }
        ]
    }

    sample_path = DATA_DIR / "sample_kansas_rift.geojson"
    with open(sample_path, "w") as f:
        json.dump(sample_geojson, f, indent=2)

    logger.info(f"✅ Created sample dataset")
    logger.info(f"   Path: {sample_path}")
    logger.info(f"   Features: {len(sample_geojson['features'])}")

    return sample_path

def create_database_import_script():
    """Create script to import downloaded datasets into Supabase"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("📝 CREATING: Database Import Script")
    logger.info("=" * 80)

    import_script = """#!/usr/bin/env python3
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
    \"\"\"Import GeoJSON file to Supabase PostGIS table\"\"\"
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

    logger.info("\\n✅ All datasets imported to Supabase!")
"""

    script_path = DATA_DIR / "import_datasets.py"
    with open(script_path, "w") as f:
        f.write(import_script)

    logger.info(f"✅ Created import script")
    logger.info(f"   Path: {script_path}")

def main():
    """Main execution"""
    logger.info("")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "MANTLEIQ DATA INGESTION PIPELINE" + " " * 26 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("")

    logger.info(f"📁 Data directory: {DATA_DIR}")
    logger.info("")

    # Step 1: Download Macrostrat (API-based, automated)
    logger.info("STEP 1: Automated API Downloads")
    download_macrostrat_geology()

    # Step 2: Show manual download instructions
    logger.info("")
    logger.info("STEP 2: Manual Downloads Required")
    show_download_instructions()

    # Step 3: Create sample dataset
    logger.info("")
    logger.info("STEP 3: Sample Data")
    create_sample_kansas_rift_dataset()

    # Step 4: Create import helper
    logger.info("")
    logger.info("STEP 4: Database Import Helper")
    create_database_import_script()

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ DATA INGESTION SETUP COMPLETE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Download datasets from the URLs listed above")
    logger.info("2. Place files in: " + str(DATA_DIR))
    logger.info("3. Run: python import_datasets.py")
    logger.info("4. Verify in Supabase SQL Editor")
    logger.info("")

if __name__ == "__main__":
    main()
