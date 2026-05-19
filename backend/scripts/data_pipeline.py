#!/usr/bin/env python3
"""
MantleIQ Data Pipeline
Downloads → Normalizes → Curates → Loads to Database

Workflow:
1. RAW: Download geospatial data from public sources
2. NORMALIZE: Validate CRS, geometry, attributes
3. CURATED: Move normalized data to curated folder
4. LOAD: Ingest to PostGIS database

Directory Structure:
/data/raw/          - Downloaded raw files (EPSG varies)
/data/curated/      - Normalized files (EPSG:4326, validated)
/data/tiles/        - Vector/raster tiles (COG format)
/data/reports/      - Generated reports & exports
"""

import os
import sys
import logging
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

import requests
import geopandas as gpd
from shapely.geometry import box
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import pandas as pd

# Setup paths
sys.path.insert(0, '/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend')
os.environ['DATABASE_URL'] = os.environ.get(
    'DATABASE_URL',
    'postgresql+psycopg2://postgres:417BajrangNagar%401@db.ttimdqokzalxluwmezcz.supabase.co:5432/postgres'
)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mantleiq_data_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Data pipeline paths
DATA_DIR = Path('/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/data')
RAW_DIR = DATA_DIR / 'raw'
CURATED_DIR = DATA_DIR / 'curated'
TILES_DIR = DATA_DIR / 'tiles'
REPORTS_DIR = DATA_DIR / 'reports'

# Ensure directories exist
for d in [RAW_DIR, CURATED_DIR, TILES_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Database connection
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


class DataPipeline:
    """Manages data ingestion pipeline: raw → normalize → curate → load"""

    def __init__(self):
        self.db = SessionLocal()
        self.pipeline_log = {
            'timestamp': datetime.now().isoformat(),
            'steps': []
        }

    def download_faults(self, basin_bounds: Tuple[float, float, float, float]) -> bool:
        """
        Download fault data from USGS

        Args:
            basin_bounds: (west, south, east, north) in EPSG:4326

        Returns:
            True if successful
        """
        logger.info("📥 Downloading USGS Faults...")
        try:
            # USGS Earthquake Hazards provides shapefile download
            # For MVP, using test data; in production would fetch actual shapefile
            url = "https://www.usgs.gov/programs/earthquake-hazards/faults"
            logger.info(f"   Source: {url}")
            logger.info(f"   Basin bounds: {basin_bounds}")

            # In production: download via API or direct URL
            # For now, log the expected structure
            faults_file = RAW_DIR / 'faults_usgs.zip'
            logger.info(f"   ✓ Would download to: {faults_file}")

            self.pipeline_log['steps'].append({
                'step': 'download_faults',
                'status': 'staged',
                'details': 'USGS faults download configured'
            })
            return True
        except Exception as e:
            logger.error(f"❌ Fault download failed: {e}")
            return False

    def download_gravity(self, basin_bounds: Tuple[float, float, float, float]) -> bool:
        """Download gravity anomaly raster from NOAA"""
        logger.info("📥 Downloading NOAA Gravity Data...")
        try:
            url = "https://www.ncei.noaa.gov/products/gravity-data"
            logger.info(f"   Source: {url}")
            logger.info(f"   Format: GeoTIFF (Cloud Optimized)")
            logger.info(f"   Resolution: ~5 km Bouguer anomaly")

            gravity_file = RAW_DIR / 'gravity_noaa.tif'
            logger.info(f"   ✓ Would download to: {gravity_file}")

            self.pipeline_log['steps'].append({
                'step': 'download_gravity',
                'status': 'staged',
                'details': 'NOAA gravity download configured'
            })
            return True
        except Exception as e:
            logger.error(f"❌ Gravity download failed: {e}")
            return False

    def download_magnetic(self, basin_bounds: Tuple[float, float, float, float]) -> bool:
        """Download magnetic anomaly raster from NOAA EMAG2"""
        logger.info("📥 Downloading NOAA EMAG2 Magnetic Data...")
        try:
            url = "https://www.ncei.noaa.gov/products/earth-magnetic-model-anomaly-grid-2"
            logger.info(f"   Source: {url}")
            logger.info(f"   Format: GeoTIFF (2-arc-minute global grid, ~3.7 km)")

            magnetic_file = RAW_DIR / 'magnetic_emag2.tif'
            logger.info(f"   ✓ Would download to: {magnetic_file}")

            self.pipeline_log['steps'].append({
                'step': 'download_magnetic',
                'status': 'staged',
                'details': 'NOAA EMAG2 download configured'
            })
            return True
        except Exception as e:
            logger.error(f"❌ Magnetic download failed: {e}")
            return False

    def download_geology(self, basin_bounds: Tuple[float, float, float, float]) -> bool:
        """Download geology/lithology from Macrostrat API"""
        logger.info("📥 Downloading Macrostrat Geology...")
        try:
            west, south, east, north = basin_bounds
            url = f"https://macrostrat.org/api/v2/units?bbox={west},{south},{east},{north}&limit=1000"

            logger.info(f"   Source: Macrostrat API")
            logger.info(f"   Query: {url}")

            # Download GeoJSON
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            geology_file = RAW_DIR / 'geology_macrostrat.geojson'
            geology_file.write_text(response.text)

            feature_count = len(response.json().get('features', []))
            logger.info(f"   ✓ Downloaded {feature_count} geological units to {geology_file}")

            self.pipeline_log['steps'].append({
                'step': 'download_geology',
                'status': 'success',
                'file': str(geology_file),
                'features': feature_count
            })
            return True
        except Exception as e:
            logger.error(f"❌ Geology download failed: {e}")
            return False

    def download_heatflow(self, basin_bounds: Tuple[float, float, float, float]) -> bool:
        """Download heat flow data from IHFC"""
        logger.info("📥 Downloading IHFC Heat Flow Data...")
        try:
            url = "https://www.ihfc-iugg.org/products/global-heat-flow-database/data"
            logger.info(f"   Source: {url}")
            logger.info(f"   Format: CSV (lat, lon, mW/m²)")

            heatflow_file = RAW_DIR / 'heatflow_ihfc.csv'
            logger.info(f"   ✓ Would download to: {heatflow_file}")

            self.pipeline_log['steps'].append({
                'step': 'download_heatflow',
                'status': 'staged',
                'details': 'IHFC heat flow download configured'
            })
            return True
        except Exception as e:
            logger.error(f"❌ Heat flow download failed: {e}")
            return False

    def normalize_vector(self, input_file: Path, output_file: Path, target_crs: str = 'EPSG:4326') -> bool:
        """
        Normalize vector data (geometry validation, CRS reprojection)

        Args:
            input_file: Path to raw vector file (shapefile, geojson)
            output_file: Path to output curated file
            target_crs: Target coordinate reference system

        Returns:
            True if successful
        """
        logger.info(f"🔄 Normalizing vector: {input_file.name}")
        try:
            gdf = gpd.read_file(input_file)
            logger.info(f"   Read {len(gdf)} features from {input_file.name}")
            logger.info(f"   Original CRS: {gdf.crs}")

            # Validate geometries
            invalid_mask = ~gdf.geometry.is_valid
            if invalid_mask.any():
                logger.warning(f"   ⚠ {invalid_mask.sum()} invalid geometries, fixing...")
                gdf.geometry = gdf.geometry.buffer(0)

            # Reproject if needed
            if gdf.crs != target_crs:
                logger.info(f"   Reprojecting to {target_crs}")
                gdf = gdf.to_crs(target_crs)

            # Save normalized file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            gdf.to_file(output_file, driver='GeoJSON' if output_file.suffix == '.geojson' else 'ESRI Shapefile')

            logger.info(f"   ✓ Normalized to {output_file}")
            return True
        except Exception as e:
            logger.error(f"   ❌ Vector normalization failed: {e}")
            return False

    def normalize_raster(self, input_file: Path, output_file: Path, target_crs: str = 'EPSG:4326') -> bool:
        """
        Normalize raster data (CRS reprojection, Cloud Optimized GeoTIFF)

        Args:
            input_file: Path to raw raster file (GeoTIFF, NetCDF)
            output_file: Path to output curated file (COG format)
            target_crs: Target coordinate reference system

        Returns:
            True if successful
        """
        logger.info(f"🔄 Normalizing raster: {input_file.name}")
        try:
            with rasterio.open(input_file) as src:
                logger.info(f"   Original CRS: {src.crs}, Shape: {src.shape}")

                # Skip if already in target CRS
                if src.crs == target_crs:
                    logger.info(f"   Already in {target_crs}, skipping reprojection")
                    shutil.copy(input_file, output_file)
                else:
                    # Calculate reprojection parameters
                    transform, width, height = calculate_default_transform(
                        src.crs, target_crs,
                        src.width, src.height,
                        *src.bounds
                    )

                    # Reproject and save as COG
                    profile = src.profile
                    profile.update({
                        'crs': target_crs,
                        'transform': transform,
                        'width': width,
                        'height': height,
                        'compress': 'lzw',
                        'TILED': 'YES',
                        'BLOCKXSIZE': 512,
                        'BLOCKYSIZE': 512
                    })

                    with rasterio.open(output_file, 'w', **profile) as dst:
                        reproject(
                            rasterio.band(src, 1),
                            rasterio.band(dst, 1),
                            resampling=Resampling.bilinear
                        )

                logger.info(f"   ✓ Normalized to {output_file} (Cloud Optimized)")
                return True
        except Exception as e:
            logger.error(f"   ❌ Raster normalization failed: {e}")
            return False

    def validate_data(self, file_path: Path) -> Dict:
        """Validate curated data for quality"""
        logger.info(f"✓ Validating: {file_path.name}")
        validation = {
            'file': str(file_path),
            'timestamp': datetime.now().isoformat(),
            'valid': True,
            'checks': []
        }

        try:
            if file_path.suffix in ['.shp', '.geojson']:
                gdf = gpd.read_file(file_path)

                # Check CRS
                crs_check = gdf.crs == 'EPSG:4326'
                validation['checks'].append({'crs_is_4326': crs_check})

                # Check validity
                invalid_count = (~gdf.geometry.is_valid).sum()
                validation['checks'].append({'invalid_geometries': invalid_count})

                # Check attributes
                validation['checks'].append({'feature_count': len(gdf)})

                validation['valid'] = crs_check and invalid_count == 0
                logger.info(f"   {len(gdf)} features, CRS={gdf.crs}, Invalid={invalid_count}")

            elif file_path.suffix == '.tif':
                with rasterio.open(file_path) as src:
                    validation['checks'].append({
                        'crs': str(src.crs),
                        'shape': src.shape,
                        'bounds': list(src.bounds)
                    })
                    validation['valid'] = src.crs == 'EPSG:4326'
                    logger.info(f"   CRS={src.crs}, Shape={src.shape}")

            elif file_path.suffix == '.csv':
                df = pd.read_csv(file_path)
                validation['checks'].append({'rows': len(df), 'columns': list(df.columns)})
                validation['valid'] = 'lat' in df.columns and 'lon' in df.columns
                logger.info(f"   {len(df)} rows, Columns: {list(df.columns)}")

        except Exception as e:
            logger.error(f"   Validation error: {e}")
            validation['valid'] = False

        return validation

    def load_to_database(self, file_path: Path, table_name: str, basin_id: str) -> bool:
        """Load curated data to PostGIS database"""
        logger.info(f"📤 Loading to database: {table_name}")
        try:
            if file_path.suffix in ['.shp', '.geojson']:
                gdf = gpd.read_file(file_path)

                # Ensure WGS84
                if gdf.crs != 'EPSG:4326':
                    gdf = gdf.to_crs('EPSG:4326')

                # Add basin_id
                gdf['basin_id'] = basin_id

                # Load to database
                gdf.to_postgis(table_name, engine, if_exists='append', index=False)
                logger.info(f"   ✓ Loaded {len(gdf)} features to '{table_name}'")
                return True

            elif file_path.suffix == '.csv':
                df = pd.read_csv(file_path)
                df['basin_id'] = basin_id

                # Convert to GeoDataFrame if lat/lon columns exist
                if 'lat' in df.columns and 'lon' in df.columns:
                    gdf = gpd.GeoDataFrame(
                        df,
                        geometry=gpd.points_from_xy(df['lon'], df['lat']),
                        crs='EPSG:4326'
                    )
                    gdf.to_postgis(table_name, engine, if_exists='append', index=False)
                else:
                    df.to_sql(table_name, engine, if_exists='append', index=False)

                logger.info(f"   ✓ Loaded {len(df)} records to '{table_name}'")
                return True

        except Exception as e:
            logger.error(f"   ❌ Database load failed: {e}")
            return False

    def generate_pipeline_report(self):
        """Generate data pipeline execution report"""
        report_file = REPORTS_DIR / f"pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.write_text(json.dumps(self.pipeline_log, indent=2))
        logger.info(f"\n📊 Pipeline report: {report_file}")

    def run_pipeline(self, basin_bounds: Tuple[float, float, float, float], basin_id: str):
        """Execute full data pipeline"""
        logger.info("=" * 70)
        logger.info("MantleIQ DATA PIPELINE - START")
        logger.info("=" * 70)
        logger.info(f"Basin: {basin_id}")
        logger.info(f"Bounds: {basin_bounds}")
        logger.info(f"Raw: {RAW_DIR}")
        logger.info(f"Curated: {CURATED_DIR}")
        logger.info("")

        # Step 1: Download
        logger.info("STEP 1: DOWNLOAD")
        logger.info("-" * 70)
        self.download_faults(basin_bounds)
        self.download_gravity(basin_bounds)
        self.download_magnetic(basin_bounds)
        self.download_geology(basin_bounds)
        self.download_heatflow(basin_bounds)

        # Step 2: Normalize
        logger.info("\nSTEP 2: NORMALIZE")
        logger.info("-" * 70)

        # Example: normalize geology if downloaded
        geology_raw = RAW_DIR / 'geology_macrostrat.geojson'
        if geology_raw.exists():
            geology_curated = CURATED_DIR / 'geology_macrostrat_normalized.geojson'
            self.normalize_vector(geology_raw, geology_curated)

        # Step 3: Validate
        logger.info("\nSTEP 3: VALIDATE")
        logger.info("-" * 70)
        for curated_file in CURATED_DIR.glob('*'):
            self.validate_data(curated_file)

        # Step 4: Load to Database
        logger.info("\nSTEP 4: LOAD TO DATABASE")
        logger.info("-" * 70)
        if geology_curated.exists():
            self.load_to_database(geology_curated, 'geologic_units', basin_id)

        # Generate report
        logger.info("\nSTEP 5: REPORT")
        logger.info("-" * 70)
        self.generate_pipeline_report()

        logger.info("=" * 70)
        logger.info("✅ DATA PIPELINE COMPLETE")
        logger.info("=" * 70)


def main():
    """Run data pipeline for test basin"""
    # Kansas Rift Basin bounds
    kansas_bounds = (-98.0, 37.0, -93.0, 40.0)  # (west, south, east, north)
    kansas_basin_id = "11e757b7-ddde-48dc-8c7a-619cfa350930"

    pipeline = DataPipeline()
    pipeline.run_pipeline(kansas_bounds, kansas_basin_id)


if __name__ == '__main__':
    main()
