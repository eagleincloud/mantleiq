# MantleIQ Data Pipeline

Complete geospatial data ingestion workflow: **Download → Normalize → Curate → Load to Database**

## 📁 Directory Structure

```
/data/
├── raw/                 # Downloaded raw files (original CRS, formats may vary)
│   ├── faults/          # USGS fault shapefiles
│   ├── gravity/         # NOAA raster files (raw GeoTIFF)
│   ├── magnetic/        # NOAA EMAG2 raster files
│   ├── geology/         # Macrostrat GeoJSON
│   └── heatflow/        # IHFC CSV point data
│
├── curated/             # Normalized, validated files (EPSG:4326, Cloud Optimized)
│   ├── faults/
│   ├── gravity/         # Cloud Optimized GeoTIFF (COG)
│   ├── magnetic/        # COG format
│   ├── geology/         # GeoJSON, validated
│   └── heatflow/        # CSV with geometry
│
├── tiles/               # Vector/raster tiles for web rendering
│   ├── fault_tiles.pbf
│   ├── geology_tiles.pbf
│   └── gravity_tiles/   # Cloud Optimized GeoTIFF
│
└── reports/             # Generated pipeline reports & exports
    ├── pipeline_report_*.json
    └── data_quality_*.html
```

## 🔄 Pipeline Workflow

### **Stage 1: DOWNLOAD**
Raw files are downloaded from public sources to `/raw/` folder.

| Data Type | Source | Format | Folder |
|-----------|--------|--------|--------|
| **Faults** | USGS Earthquake Hazards | Shapefile (.shp/.zip) | `raw/faults/` |
| **Gravity** | NOAA/NCEI | GeoTIFF (.tif) | `raw/gravity/` |
| **Magnetic** | NOAA EMAG2 v3 | GeoTIFF (.tif) | `raw/magnetic/` |
| **Geology** | Macrostrat API | GeoJSON (.geojson) | `raw/geology/` |
| **Heatflow** | IHFC Database | CSV (.csv) | `raw/heatflow/` |

**Sources:**
- Faults: https://www.usgs.gov/programs/earthquake-hazards/faults
- Gravity: https://www.ncei.noaa.gov/products/gravity-data
- Magnetic: https://www.ncei.noaa.gov/products/earth-magnetic-model-anomaly-grid-2
- Geology: https://macrostrat.org/api/v2
- Heatflow: https://www.ihfc-iugg.org/products/global-heat-flow-database/data

### **Stage 2: NORMALIZE**
Raw files are processed to ensure consistency:

✓ **CRS Validation & Reprojection** → All files converted to EPSG:4326 (WGS84)
✓ **Geometry Validation** → Fix/remove invalid geometries
✓ **Attribute Validation** → Ensure required fields present
✓ **Cloud Optimization** → Rasters converted to COG format
✓ **Format Standardization** → Vector: GeoJSON, Raster: GeoTIFF

**Normalized files stored in `/curated/`**

### **Stage 3: VALIDATE**
Quality assurance checks on curated files:

- ✓ CRS is EPSG:4326
- ✓ All geometries are valid
- ✓ Feature/record count logged
- ✓ Spatial extent within basin bounds
- ✓ Required attributes present
- ✓ Data types correct

### **Stage 4: LOAD**
Validated data imported to PostGIS database:

```sql
-- Vector data (faults, geology, heatflow points)
INSERT INTO geologic_units (id, basin_id, geometry, lithology_class, ...)
INSERT INTO faults (id, basin_id, geometry, fault_name, ...)
INSERT INTO heatflow_points (id, basin_id, geometry, heatflow_mwm2, ...)

-- Raster metadata (gravity, magnetic tiles)
INSERT INTO gravity_tiles (id, basin_id, raster_path, resolution, ...)
INSERT INTO magnetic_tiles (id, basin_id, raster_path, resolution, ...)
```

### **Stage 5: REPORT**
Pipeline execution logged to JSON report:

```json
{
  "timestamp": "2026-05-12T10:30:00",
  "basin_id": "11e757b7-ddde-48dc-8c7a-619cfa350930",
  "steps": [
    {
      "step": "download_geology",
      "status": "success",
      "file": "data/raw/geology_macrostrat.geojson",
      "features": 245
    },
    {
      "step": "normalize_geology",
      "status": "success",
      "output": "data/curated/geology_normalized.geojson"
    },
    {
      "step": "validate_geometry",
      "valid": true,
      "invalid_count": 0
    },
    {
      "step": "load_database",
      "status": "success",
      "records_loaded": 245
    }
  ]
}
```

## 🚀 Usage

### Run Full Pipeline
```bash
cd /Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend

# Run complete pipeline (download → normalize → validate → load)
python3 scripts/data_pipeline.py

# Output:
# ======================================================================
# MantleIQ DATA PIPELINE - START
# ======================================================================
# STEP 1: DOWNLOAD
# 📥 Downloading USGS Faults...
# 📥 Downloading NOAA Gravity Data...
# ...
# STEP 2: NORMALIZE
# 🔄 Normalizing vector: geology_macrostrat.geojson
# ...
# STEP 3: VALIDATE
# ✓ Validating: geology_normalized.geojson
# ...
# STEP 4: LOAD TO DATABASE
# 📤 Loading to database: geologic_units
# ...
# ✅ DATA PIPELINE COMPLETE
```

### Download Specific Data Type
```python
from backend.scripts.data_pipeline import DataPipeline

pipeline = DataPipeline()
kansas_bounds = (-98.0, 37.0, -93.0, 40.0)

# Download geology only
pipeline.download_geology(kansas_bounds)

# Normalize downloaded file
from pathlib import Path
pipeline.normalize_vector(
    Path('data/raw/geology_macrostrat.geojson'),
    Path('data/curated/geology_normalized.geojson')
)
```

### Manual Normalization
```python
from geopandas import read_file

# Read raw file
gdf = read_file('data/raw/faults_usgs.shp')

# Reproject to WGS84
gdf = gdf.to_crs('EPSG:4326')

# Fix invalid geometries
gdf.geometry = gdf.geometry.buffer(0)

# Save curated file
gdf.to_file('data/curated/faults_normalized.geojson', driver='GeoJSON')
```

## 📊 Data Validation Checklist

For each data type, validation ensures:

### Faults (Vector)
- [ ] CRS is EPSG:4326
- [ ] All geometries are valid LineStrings
- [ ] No self-intersecting lines
- [ ] Required fields: fault_name, activity_class
- [ ] Spatial extent: within basin bounds ±1°

### Gravity/Magnetic (Raster)
- [ ] CRS is EPSG:4326
- [ ] Format: Cloud Optimized GeoTIFF
- [ ] NoData value defined
- [ ] Tiled structure (512×512 blocks)
- [ ] Resolution documented in metadata

### Geology (Vector)
- [ ] CRS is EPSG:4326
- [ ] All geometries are valid Polygons
- [ ] No overlapping features (except by design)
- [ ] Required fields: lithology_class, age_range
- [ ] Covers basin extent

### Heatflow (Point)
- [ ] CRS is EPSG:4326
- [ ] All geometries are valid Points
- [ ] Required fields: lat, lon, heatflow_mwm2
- [ ] Values within realistic range (0-300 mW/m²)
- [ ] No duplicate locations

## 🔧 Configuration

Pipeline behavior configured in `/config/datasets.yaml`:

```yaml
datasets:
  faults_usgs:
    source_url: "https://www.usgs.gov/programs/earthquake-hazards/faults"
    type: vector
    format: shapefile
    target_table: faults
    priority: critical
    required: true
    crs: EPSG:4326

  gravity_noaa:
    source_url: "https://www.ncei.noaa.gov/products/gravity-data"
    type: raster
    format: geotiff
    target_table: gravity_tiles
    priority: critical
    resolution: "~5 km"
    crs: EPSG:4326
```

## 📈 Data Acquisition Strategy by Phase

| Phase | Datasets | Status |
|-------|----------|--------|
| **Phase 1** | Basins, Faults, Gravity, Magnetic, Geology, Heatflow, DEM | ✅ Configured |
| **Phase 2** | Surface Indicators, GLiM Global Lithology | 🟡 Planned |
| **Phase 3** | Seismic, Well Logs, Proprietary Data | ⏳ Future |

## ⚠️ Important Notes

### File Size Expectations
- Faults (Kansas Rift): ~50 MB
- Gravity Raster: ~500 MB (full tile), ~50 MB (basin clip)
- Magnetic Raster: ~500 MB
- Geology (Macrostrat): ~20-100 MB
- Heatflow: ~5-10 MB

### Storage Requirements
- Raw folder: ~2-3 GB for full basin suite
- Curated folder: ~1-2 GB (after normalization)
- Total with tiles: ~3-5 GB

### Download Time
- Average: 10-30 minutes per data type (depends on internet speed)
- Parallelization possible for independent downloads

### Database Impact
- Geometry indices created automatically
- Spatial queries optimized with GIST/BRIN indices
- Estimated load time: 5-15 minutes per basin

## 🐛 Troubleshooting

### "CRS mismatch" Error
```python
# Fix: Explicitly reproject
gdf = gdf.to_crs('EPSG:4326')
gdf.to_file('data/curated/fixed.geojson', driver='GeoJSON')
```

### "Invalid geometry" Errors
```python
# Fix: Buffer and re-validate
gdf.geometry = gdf.geometry.buffer(0)
gdf = gdf[gdf.geometry.is_valid]
```

### "Database connection timeout"
```bash
# Check database connectivity
python3 -c "from app.core.config import settings; print(settings.database_url)"

# Verify Supabase is running
curl https://db.ttimdqokzalxluwmezcz.supabase.co/rest/v1/basins
```

## 📞 Support

For questions about data pipeline:
1. Check `/reports/` for execution logs
2. Review `/data/curated/` for successful outputs
3. Inspect database with: `SELECT table_name FROM information_schema.tables WHERE table_schema='public'`

## 📚 Related Documentation

- Data Sources: [datasets.yaml](../config/datasets.yaml)
- Model Config: [model.yaml](../config/model.yaml)
- Database Schema: [orm.py](../app/models/orm.py)
- Execution Strategy: [MANTLEIQ_UPDATED_EXECUTION_STRATEGY.md](../../MANTLEIQ_UPDATED_EXECUTION_STRATEGY.md)

---

**Last Updated:** 2026-05-12
**Status:** Production Ready
**Test Basin:** Kansas Rift (11e757b7-ddde-48dc-8c7a-619cfa350930)
