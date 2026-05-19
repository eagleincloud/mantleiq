#!/usr/bin/env python3
"""
Generate realistic synthetic geospatial data for Kansas Rift Basin
Matches actual feature schema for immediate model training and testing
"""

import logging
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/local_storage/datasets")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def create_geospatial_features_geojson():
    """Create realistic geospatial features GeoJSON for Kansas Rift region"""
    logger.info("=" * 80)
    logger.info("CREATING: Realistic Geospatial Features Dataset")
    logger.info("=" * 80)

    # Kansas Rift bounds
    west, south, east, north = -98, 37, -93, 40

    features = []

    # 1. Fault lines (Nemaha Ridge, several mapped faults)
    fault_coords = [
        [(-96.5, 37.2), (-96, 38), (-95.5, 39), (-95, 40)],
        [(-97, 37.5), (-96.5, 38.5), (-96, 39.5)],
        [(-94.5, 37.8), (-94, 38.5), (-93.5, 39.2)],
    ]
    for i, coords in enumerate(fault_coords):
        features.append({
            "type": "Feature",
            "properties": {
                "name": f"Fault {i+1}",
                "fault_type": "normal",
                "activity_class": "quaternary" if i == 0 else "holocene",
                "confidence": 0.85 + np.random.random() * 0.1,
            },
            "geometry": {"type": "LineString", "coordinates": coords}
        })

    # 2. Ultramafic/mafic intrusions
    for i in range(8):
        lon = west + (i % 4) * (east - west) / 4 + np.random.normal(0, 0.3)
        lat = south + (i // 4) * (north - south) / 2 + np.random.normal(0, 0.3)

        features.append({
            "type": "Feature",
            "properties": {
                "name": f"Ultramafic Body {i+1}",
                "rock_type": "ultramafic" if i % 2 == 0 else "mafic",
                "age_ma": 500 + np.random.randint(-100, 100),
                "extent_km2": 50 + np.random.randint(20, 200),
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]}
        })

    # 3. Heat flow measurement points
    for i in range(12):
        lon = west + np.random.random() * (east - west)
        lat = south + np.random.random() * (north - south)
        heatflow = 50 + np.random.normal(20, 10)  # mW/m²

        features.append({
            "type": "Feature",
            "properties": {
                "measurement_type": "borehole",
                "heatflow_mw_m2": max(20, heatflow),
                "depth_m": 500 + np.random.randint(500, 2000),
                "quality": ["good", "fair"][np.random.randint(0, 2)],
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]}
        })

    # 4. Basin boundaries and structural features
    basin_features = [
        {"type": "Polygon", "name": "Kansas Rift Main Basin", "struct_class": "rift"},
        {"type": "Polygon", "name": "Secondary Graben", "struct_class": "graben"},
    ]

    for i, basin_feat in enumerate(basin_features):
        if basin_feat["type"] == "Polygon":
            coords = [[
                [west + i*0.5, south],
                [west + i*0.5 + 2, south],
                [west + i*0.5 + 2, south + 1.5],
                [west + i*0.5, south + 1.5],
                [west + i*0.5, south]
            ]]
            features.append({
                "type": "Feature",
                "properties": {
                    "name": basin_feat["name"],
                    "structural_class": basin_feat["struct_class"],
                    "depth_to_basement_km": 2 + np.random.random() * 3,
                },
                "geometry": {"type": "Polygon", "coordinates": coords}
            })

    geojson = {"type": "FeatureCollection", "features": features}

    output_path = DATA_DIR / "kansas_rift_geospatial_features.geojson"
    with open(output_path, "w") as f:
        json.dump(geojson, f, indent=2)

    logger.info(f"✅ Created geospatial features: {len(features)} features")
    logger.info(f"   Path: {output_path}")
    return output_path

def create_grid_features_csv():
    """Create realistic grid-based feature values for model training"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("CREATING: Grid Cell Features (for ML training)")
    logger.info("=" * 80)

    west, south, east, north = -98, 37, -93, 40
    grid_size = 0.5  # 0.5 degree cells

    data = []
    cell_id = 0

    lon = west
    while lon < east:
        lat = south
        while lat < north:
            cell_id += 1

            # Realistic feature correlations
            fault_proximity = np.random.exponential(5, 1)[0]  # Distance to nearest fault (km)
            fault_density = max(0, 10 - fault_proximity) / 10  # Higher where faults are close

            ultramafic_proximity = np.random.exponential(15, 1)[0]  # Distance to ultramafic
            ultramafic_fraction = max(0, min(10, 15 - ultramafic_proximity)) / 10 * 100  # %

            # Gravity anomaly (mGal) - typically 0-100 in rift zones
            gravity_gradient = 20 + np.random.normal(0, 15)

            # Magnetic anomaly - typically 0-500 nT
            magnetic_gradient = 100 + np.random.normal(0, 80)

            # Heat flow (mW/m²)
            heatflow = 50 + np.random.normal(10, 15)

            # Structural complexity (0-1)
            structural_complexity = fault_density + np.random.uniform(0, 0.3)
            structural_complexity = min(1, structural_complexity)

            # Seep proximity (0-1, higher if near surface indicators)
            seep_proximity = np.random.uniform(0.3, 0.9)

            # Basin presence (0-1)
            basin_presence = 0.8 + np.random.uniform(-0.1, 0.2)
            basin_presence = min(1, basin_presence)

            # Caprock proxy (0-1)
            caprock_proxy = np.random.uniform(0.4, 0.95)

            # Data quality metrics
            data_coverage = 0.7 + np.random.uniform(0, 0.3)  # 0.7-1.0
            data_quality = 0.65 + np.random.uniform(0, 0.35)  # 0.65-1.0
            missing_completeness = 0.85 + np.random.uniform(-0.1, 0.15)  # 0.75-1.0
            missing_completeness = min(1, max(0, missing_completeness))

            data.append({
                "cell_id": f"cell_{cell_id:04d}",
                "lon": lon,
                "lat": lat,
                "fault_density_score": fault_density,
                "ultramafic_fraction": ultramafic_fraction,
                "gravity_gradient_score": gravity_gradient,
                "magnetic_gradient_score": magnetic_gradient,
                "heatflow_score": heatflow,
                "structural_complexity_score": structural_complexity,
                "seep_proximity_score": seep_proximity,
                "basin_presence_score": basin_presence,
                "caprock_proxy_score": caprock_proxy,
                "data_coverage": data_coverage,
                "data_quality": data_quality,
                "missing_data_completeness": missing_completeness,
            })

            lat += grid_size
        lon += grid_size

    # Write to CSV
    import csv
    output_path = DATA_DIR / "grid_features.csv"
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    logger.info(f"✅ Created {len(data)} grid cells with features")
    logger.info(f"   Path: {output_path}")
    logger.info(f"   Grid coverage: {west}°W to {east}°W, {south}°N to {north}°N")
    return output_path

def create_labeled_training_data():
    """Create labeled training data for XGBoost (prospectivity scores)"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("CREATING: Labeled Training Data (for XGBoost)")
    logger.info("=" * 80)

    n_samples = 150  # Training samples

    training_data = []
    for i in range(n_samples):
        # Realistic feature ranges based on Kansas Rift geology
        fault_density = np.random.uniform(0, 1)
        ultramafic_fraction = np.random.uniform(0, 10)
        gravity_gradient = np.random.normal(20, 15)
        magnetic_gradient = np.random.normal(100, 80)
        heatflow = np.random.normal(50, 15)
        structural_complexity = np.random.uniform(0, 1)
        seep_proximity = np.random.uniform(0, 1)
        basin_presence = np.random.uniform(0.6, 1)
        caprock_proxy = np.random.uniform(0, 1)

        # Prospectivity score formula (reasonable weights based on geology)
        prospectivity = (
            fault_density * 0.25 +  # Fault-related hydrogen generation
            min(ultramafic_fraction / 10, 1) * 0.15 +  # Ultramafic as source proxy
            min(abs(gravity_gradient) / 50, 1) * 0.15 +  # Basement structure
            min(abs(magnetic_gradient) / 300, 1) * 0.10 +  # Lithology variation
            min(heatflow / 100, 1) * 0.15 +  # Geothermal gradient
            structural_complexity * 0.10 +  # Trapping geometry
            seep_proximity * 0.05 +  # Surface indicators
            basin_presence * 0.05  # Basin geometry
        )
        prospectivity = max(0, min(1, prospectivity + np.random.normal(0, 0.1)))

        training_data.append({
            "fault_density_score": fault_density,
            "ultramafic_fraction": ultramafic_fraction,
            "gravity_gradient_score": gravity_gradient,
            "magnetic_gradient_score": magnetic_gradient,
            "heatflow_score": heatflow,
            "structural_complexity_score": structural_complexity,
            "seep_proximity_score": seep_proximity,
            "basin_presence_score": basin_presence,
            "caprock_proxy_score": caprock_proxy,
            "prospectivity_label": prospectivity,
        })

    import csv
    output_path = DATA_DIR / "training_data.csv"
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=training_data[0].keys())
        writer.writeheader()
        writer.writerows(training_data)

    logger.info(f"✅ Created {len(training_data)} labeled training samples")
    logger.info(f"   Path: {output_path}")
    return output_path

def main():
    logger.info("")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 15 + "REALISTIC SYNTHETIC DATA GENERATION" + " " * 28 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("")

    create_geospatial_features_geojson()
    create_grid_features_csv()
    create_labeled_training_data()

    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ DATASET CREATION COMPLETE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Generated files ready for:")
    logger.info("  1. XGBoost model training (training_data.csv)")
    logger.info("  2. Pipeline feature computation (grid_features.csv)")
    logger.info("  3. Geospatial visualization (kansas_rift_geospatial_features.geojson)")
    logger.info("")
    logger.info("Next: Run 'python run_supabase_pipeline.py' to train model and generate tiles")
    logger.info("")

if __name__ == "__main__":
    main()
