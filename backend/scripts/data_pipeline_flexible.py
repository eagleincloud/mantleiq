#!/usr/bin/env python3
"""
MantleIQ Flexible Data Pipeline
Downloads geospatial data with optional bounding box filtering
Supports: Full global downloads OR region-specific downloads
"""

import os
import sys
import logging
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import requests
import geopandas as gpd
from shapely.geometry import box
import pandas as pd

sys.path.insert(0, '/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend')
os.environ['DATABASE_URL'] = os.environ.get(
    'DATABASE_URL',
    'postgresql+psycopg2://postgres:417BajrangNagar%401@db.ttimdqokzalxluwmezcz.supabase.co:5432/postgres'
)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mantleiq_data_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DATA_DIR = Path('/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/data')
RAW_DIR = DATA_DIR / 'raw'
CURATED_DIR = DATA_DIR / 'curated'
TILES_DIR = DATA_DIR / 'tiles'
REPORTS_DIR = DATA_DIR / 'reports'

for d in [RAW_DIR, CURATED_DIR, TILES_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


# Pre-defined basins/regions
BASINS = {
    'kansas_rift': {
        'name': 'Kansas Rift Basin',
        'bounds': (-98.0, 37.0, -93.0, 40.0),  # (west, south, east, north)
        'description': 'Central US natural hydrogen prospectivity'
    },
    'permian': {
        'name': 'Permian Basin',
        'bounds': (-104.0, 30.0, -98.0, 36.0),
        'description': 'Texas-New Mexico natural hydrogen system'
    },
    'gulf_coast': {
        'name': 'Gulf Coast Basin',
        'bounds': (-97.0, 25.0, -88.0, 30.0),
        'description': 'Gulf of Mexico coastal hydrogen province'
    },
    'illinois': {
        'name': 'Illinois Basin',
        'bounds': (-92.0, 36.0, -87.0, 42.0),
        'description': 'Midwestern US sedimentary system'
    },
    'global': {
        'name': 'Global (No Filter)',
        'bounds': None,  # Full global download
        'description': 'Complete global datasets'
    }
}


class FlexibleDataPipeline:
    """Data pipeline supporting optional bounding box filtering"""

    def __init__(self, basin_name: str = 'kansas_rift', use_bounds: bool = True):
        """
        Initialize pipeline for a specific basin

        Args:
            basin_name: Key from BASINS dict ('kansas_rift', 'permian', 'global', etc.)
            use_bounds: If True, filter to basin bounds. If False, download full dataset
        """
        if basin_name not in BASINS:
            raise ValueError(f"Unknown basin: {basin_name}. Choose from: {list(BASINS.keys())}")

        self.basin_name = basin_name
        self.basin_config = BASINS[basin_name]
        self.use_bounds = use_bounds and self.basin_config['bounds'] is not None
        self.bounds = self.basin_config['bounds'] if self.use_bounds else None
        self.db = SessionLocal()
        self.pipeline_log = {
            'timestamp': datetime.now().isoformat(),
            'basin': basin_name,
            'bounds': self.bounds,
            'use_bounds': self.use_bounds,
            'steps': []
        }

        logger.info(f"\n{'='*70}")
        logger.info(f"Basin: {self.basin_config['name']}")
        logger.info(f"Description: {self.basin_config['description']}")
        if self.use_bounds:
            logger.info(f"Bounds: {self.bounds} (west, south, east, north)")
        else:
            logger.info(f"Bounds: NONE - Downloading full global dataset")
        logger.info(f"{'='*70}\n")

    def download_geology(self, force_redownload: bool = False) -> bool:
        """
        Download geology from Macrostrat API (no bounds filter available)

        Args:
            force_redownload: If True, overwrite existing file

        Returns:
            True if successful
        """
        logger.info("📥 Downloading Macrostrat Geology...")

        if self.bounds:
            west, south, east, north = self.bounds
            url = f"https://macrostrat.org/api/v2/units?bbox={west},{south},{east},{north}&limit=1000"
            logger.info(f"   Query: {url}")
            output_file = RAW_DIR / 'geology' / f'geology_macrostrat_{self.basin_name}.geojson'
        else:
            url = "https://macrostrat.org/api/v2/units?limit=1000"
            logger.info(f"   Query: {url} (GLOBAL - no bounds)")
            output_file = RAW_DIR / 'geology' / 'geology_macrostrat_global.geojson'

        # Check if file exists
        if output_file.exists() and not force_redownload:
            logger.info(f"   ⚠ File exists: {output_file}")
            logger.info(f"   (Use force_redownload=True to overwrite)")
            self.pipeline_log['steps'].append({
                'step': 'download_geology',
                'status': 'skipped',
                'reason': 'file_exists',
                'file': str(output_file)
            })
            return True

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(response.text)

            feature_count = len(response.json().get('features', []))
            logger.info(f"   ✓ Downloaded {feature_count} features to {output_file}")

            self.pipeline_log['steps'].append({
                'step': 'download_geology',
                'status': 'success',
                'file': str(output_file),
                'features': feature_count
            })
            return True
        except Exception as e:
            logger.error(f"   ❌ Download failed: {e}")
            self.pipeline_log['steps'].append({
                'step': 'download_geology',
                'status': 'failed',
                'error': str(e)
            })
            return False

    def download_faults(self, force_redownload: bool = False) -> bool:
        """
        Configure USGS faults download

        Args:
            force_redownload: If True, mark for redownload
        """
        logger.info("📥 Configuring USGS Faults Download...")

        url = "https://www.usgs.gov/programs/earthquake-hazards/faults"
        logger.info(f"   Source: {url}")

        if self.use_bounds:
            logger.info(f"   Bounds: {self.bounds}")
            output_file = RAW_DIR / 'faults' / f'faults_usgs_{self.basin_name}.zip'
        else:
            logger.info(f"   Bounds: GLOBAL (full dataset)")
            output_file = RAW_DIR / 'faults' / 'faults_usgs_global.zip'

        if output_file.exists() and not force_redownload:
            logger.info(f"   ⚠ File exists: {output_file}")
            logger.info(f"   (Use force_redownload=True to re-download)")
            return True

        logger.info(f"   ✓ Would download to: {output_file}")
        self.pipeline_log['steps'].append({
            'step': 'download_faults',
            'status': 'staged',
            'file': str(output_file),
            'note': 'Manual download required - use USGS website or wget'
        })
        return True

    def download_gravity(self, force_redownload: bool = False) -> bool:
        """Download gravity raster from NOAA"""
        logger.info("📥 Configuring NOAA Gravity Download...")

        url = "https://www.ncei.noaa.gov/products/gravity-data"
        logger.info(f"   Source: {url}")

        if self.use_bounds:
            logger.info(f"   Bounds: {self.bounds}")
            output_file = RAW_DIR / 'gravity' / f'gravity_noaa_{self.basin_name}.tif'
        else:
            logger.info(f"   Bounds: GLOBAL (full grid)")
            output_file = RAW_DIR / 'gravity' / 'gravity_noaa_global.tif'

        if output_file.exists() and not force_redownload:
            logger.info(f"   ⚠ File exists: {output_file}")
            return True

        logger.info(f"   ✓ Would download to: {output_file}")
        self.pipeline_log['steps'].append({
            'step': 'download_gravity',
            'status': 'staged',
            'file': str(output_file)
        })
        return True

    def download_magnetic(self, force_redownload: bool = False) -> bool:
        """Download magnetic raster from NOAA EMAG2"""
        logger.info("📥 Configuring NOAA EMAG2 Magnetic Download...")

        url = "https://www.ncei.noaa.gov/products/earth-magnetic-model-anomaly-grid-2"
        logger.info(f"   Source: {url}")

        if self.use_bounds:
            logger.info(f"   Bounds: {self.bounds}")
            output_file = RAW_DIR / 'magnetic' / f'magnetic_emag2_{self.basin_name}.tif'
        else:
            logger.info(f"   Bounds: GLOBAL (2-arc-minute grid)")
            output_file = RAW_DIR / 'magnetic' / 'magnetic_emag2_global.tif'

        if output_file.exists() and not force_redownload:
            logger.info(f"   ⚠ File exists: {output_file}")
            return True

        logger.info(f"   ✓ Would download to: {output_file}")
        self.pipeline_log['steps'].append({
            'step': 'download_magnetic',
            'status': 'staged',
            'file': str(output_file)
        })
        return True

    def download_heatflow(self, force_redownload: bool = False) -> bool:
        """Download heat flow data from IHFC"""
        logger.info("📥 Configuring IHFC Heat Flow Download...")

        url = "https://www.ihfc-iugg.org/products/global-heat-flow-database/data"
        logger.info(f"   Source: {url}")

        if self.use_bounds:
            logger.info(f"   Bounds: {self.bounds}")
            output_file = RAW_DIR / 'heatflow' / f'heatflow_ihfc_{self.basin_name}.csv'
        else:
            logger.info(f"   Bounds: GLOBAL (all measurements)")
            output_file = RAW_DIR / 'heatflow' / 'heatflow_ihfc_global.csv'

        if output_file.exists() and not force_redownload:
            logger.info(f"   ⚠ File exists: {output_file}")
            return True

        logger.info(f"   ✓ Would download to: {output_file}")
        self.pipeline_log['steps'].append({
            'step': 'download_heatflow',
            'status': 'staged',
            'file': str(output_file)
        })
        return True

    def list_available_basins(self):
        """Show all available basins"""
        logger.info("\n" + "="*70)
        logger.info("AVAILABLE BASINS/REGIONS")
        logger.info("="*70)
        for key, config in BASINS.items():
            bounds_str = f"Bounds: {config['bounds']}" if config['bounds'] else "Bounds: GLOBAL (No filter)"
            logger.info(f"\n  {key.upper()}")
            logger.info(f"  Name: {config['name']}")
            logger.info(f"  {bounds_str}")
            logger.info(f"  {config['description']}")
        logger.info("\n" + "="*70)

    def generate_pipeline_report(self):
        """Generate execution report"""
        report_file = REPORTS_DIR / f"pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.write_text(json.dumps(self.pipeline_log, indent=2))
        logger.info(f"\n📊 Pipeline report: {report_file}")

    def run_pipeline(self, force_redownload: bool = False):
        """Execute full download pipeline"""
        logger.info("\nSTEP 1: DOWNLOAD")
        logger.info("-" * 70)

        self.download_faults(force_redownload=force_redownload)
        self.download_gravity(force_redownload=force_redownload)
        self.download_magnetic(force_redownload=force_redownload)
        self.download_geology(force_redownload=force_redownload)
        self.download_heatflow(force_redownload=force_redownload)

        logger.info("\nSTEP 2: REPORT")
        logger.info("-" * 70)
        self.generate_pipeline_report()

        logger.info("\n" + "="*70)
        logger.info("✅ DOWNLOAD CONFIGURATION COMPLETE")
        logger.info("="*70)


def main():
    """Interactive menu for data pipeline"""
    import sys

    logger.info("\n" + "="*70)
    logger.info("MantleIQ FLEXIBLE DATA PIPELINE")
    logger.info("="*70)

    # Show basins
    pipeline = FlexibleDataPipeline()
    pipeline.list_available_basins()

    # Get user input
    logger.info("\nSELECT OPTION:")
    logger.info("1) Download for Kansas Rift (with bounds)")
    logger.info("2) Download for Permian Basin (with bounds)")
    logger.info("3) Download for Illinois Basin (with bounds)")
    logger.info("4) Download GLOBAL (no bounds, full datasets)")
    logger.info("5) Re-download same region (force overwrite)")
    logger.info("6) Exit")

    choice = input("\nEnter choice (1-6): ").strip()

    selections = {
        '1': ('kansas_rift', False),
        '2': ('permian', False),
        '3': ('illinois', False),
        '4': ('global', False),
        '5': ('kansas_rift', True),  # Force re-download
    }

    if choice in selections:
        basin, force_redownload = selections[choice]
        logger.info(f"\n{'='*70}")
        logger.info(f"Configuration: Basin={basin}, Force Redownload={force_redownload}")
        logger.info(f"{'='*70}\n")

        pipeline = FlexibleDataPipeline(basin_name=basin, use_bounds=basin != 'global')
        pipeline.run_pipeline(force_redownload=force_redownload)
    else:
        logger.info("Exiting...")


if __name__ == '__main__':
    main()
