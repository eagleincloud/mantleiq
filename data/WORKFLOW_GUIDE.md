# MantleIQ Data Pipeline - Workflow Guide

## 📊 Complete Data Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MANTLEIQ DATA PIPELINE ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────────────────┘

PUBLIC DATA SOURCES (APIs + Downloads)
│
├─ USGS Faults                    https://www.usgs.gov/programs/earthquake-hazards/faults
├─ Macrostrat Geology             https://macrostrat.org/api/v2
├─ NOAA Gravity                   https://www.ncei.noaa.gov/products/gravity-data
├─ NOAA EMAG2 Magnetic            https://www.ncei.noaa.gov/products/earth-magnetic-model-anomaly-grid-2
├─ IHFC Heat Flow                 https://www.ihfc-iugg.org/products/global-heat-flow-database/data
└─ NASA SRTM DEM                  https://www.earthdata.nasa.gov/data/instruments/srtm

        ↓ DOWNLOAD (Variable CRS, Various Formats)

┌─────────────────────────────────────────────────────────────────────────────┐
│                          STAGE 1: RAW DATA                                   │
│  /data/raw/faults/            (Shapefiles, mixed CRS)                        │
│  /data/raw/geology/           (GeoJSON, EPSG:varies)                         │
│  /data/raw/gravity/           (GeoTIFF, irregular grid)                      │
│  /data/raw/magnetic/          (GeoTIFF, various projections)                 │
│  /data/raw/heatflow/          (CSV, lat/lon columns)                         │
│  /data/raw/dem/               (GeoTIFF, SRTM format)                         │
│                                                                              │
│  Status: ❌ Variable Quality                                                 │
│  - CRS: Mixed (EPSG:4326, NAD83, others)                                     │
│  - Geometries: May contain invalid/self-intersecting                         │
│  - Formats: Shapefile, GeoTIFF, GeoJSON, CSV, NetCDF                         │
│  - File Size: 100MB - 500MB per data type                                    │
└─────────────────────────────────────────────────────────────────────────────┘

        ↓ NORMALIZE (Reproject, Validate, Standardize)

┌─────────────────────────────────────────────────────────────────────────────┐
│                        STAGE 2: NORMALIZATION                                │
│                                                                              │
│  Transformation Pipeline:                                                    │
│                                                                              │
│  VECTOR DATA (Faults, Geology, Heat Flow Points)                             │
│  ├─ Read with GeoPandas                                                      │
│  ├─ Validate geometries (fix invalid with buffer(0))                         │
│  ├─ Reproject to EPSG:4326 (WGS84)                                           │
│  ├─ Validate attribute schema (require key fields)                           │
│  ├─ Check spatial extent (must intersect basin)                              │
│  └─ Save as GeoJSON (standardized vector format)                             │
│                                                                              │
│  RASTER DATA (Gravity, Magnetic, DEM)                                        │
│  ├─ Read with Rasterio                                                       │
│  ├─ Calculate reprojection parameters                                        │
│  ├─ Reproject to EPSG:4326 using bilinear resampling                         │
│  ├─ Convert to Cloud Optimized GeoTIFF (COG)                                 │
│  │   ├─ LZW compression                                                      │
│  │   ├─ 512×512 pixel tiles (web-friendly)                                   │
│  │   └─ Spatial indexes                                                      │
│  └─ Save with spatial metadata                                               │
│                                                                              │
│  CSV DATA (Heat Flow)                                                        │
│  ├─ Read with Pandas                                                         │
│  ├─ Validate lat/lon columns                                                 │
│  ├─ Create GeoDataFrame (points_from_xy)                                      │
│  ├─ Set CRS to EPSG:4326                                                     │
│  └─ Save with geometry column                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

        ↓ MOVE TO CURATED

┌─────────────────────────────────────────────────────────────────────────────┐
│                       STAGE 3: CURATED DATA                                  │
│  /data/curated/faults/           (GeoJSON, EPSG:4326, valid)                │
│  /data/curated/geology/          (GeoJSON, EPSG:4326, complete)             │
│  /data/curated/gravity/          (Cloud Optimized GeoTIFF)                   │
│  /data/curated/magnetic/         (Cloud Optimized GeoTIFF)                   │
│  /data/curated/heatflow/         (GeoJSON, EPSG:4326)                        │
│  /data/curated/dem/              (Cloud Optimized GeoTIFF)                   │
│                                                                              │
│  Status: ✅ Production Quality                                              │
│  - CRS: All EPSG:4326 (WGS84)                                                │
│  - Geometries: Validated, no errors                                          │
│  - Format: GeoJSON (vector), Cloud-optimized GeoTIFF (raster)                │
│  - Metadata: Complete, documented                                            │
│  - Size: Reduced (normalized, clipped to basin)                              │
└─────────────────────────────────────────────────────────────────────────────┘

        ↓ VALIDATE

┌─────────────────────────────────────────────────────────────────────────────┐
│                        STAGE 4: VALIDATION                                   │
│                                                                              │
│  Quality Assurance Checks:                                                   │
│  ✓ CRS Validation        → All EPSG:4326?                                    │
│  ✓ Geometry Check        → All valid? No self-intersections?                 │
│  ✓ Attribute Check       → Required fields present?                          │
│  ✓ Spatial Extent        → Features within basin ±1°?                        │
│  ✓ Data Type Check       → Correct type (vector/raster)?                     │
│  ✓ Value Range Check     → Heat flow 0-300 mW/m²?                            │
│  ✓ Feature Count         → Expected number of features?                      │
│  ✓ Metadata Check        → All metadata fields complete?                     │
│                                                                              │
│  Report: /data/reports/pipeline_report_YYYYMMDD_HHMMSS.json                 │
│  └─ Details for each validation step                                         │
│  └─ Pass/fail status                                                         │
│  └─ Data quality score (0-100%)                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

        ↓ LOAD TO DATABASE

┌─────────────────────────────────────────────────────────────────────────────┐
│                  STAGE 5: POSTGIS DATABASE                                   │
│                                                                              │
│  PostgreSQL 15 + PostGIS 3.4                                                 │
│  (Supabase Cloud SQL - GCP Hosted)                                           │
│                                                                              │
│  VECTOR TABLES                                                               │
│  ├─ public.faults                                                            │
│  │   ├─ id (UUID, primary key)                                               │
│  │   ├─ basin_id (UUID, foreign key)                                         │
│  │   ├─ geometry (geometry, type=LineString, SRID=4326)                      │
│  │   ├─ fault_name (text)                                                    │
│  │   ├─ activity_class (text: Holocene, Quaternary, etc.)                    │
│  │   ├─ confidence (numeric: 0.0-1.0)                                        │
│  │   └─ created_at (timestamp)                                               │
│  │   Index: GIST(geometry) for spatial queries                               │
│  │                                                                           │
│  ├─ public.geologic_units                                                    │
│  │   ├─ id (UUID, primary key)                                               │
│  │   ├─ basin_id (UUID, foreign key)                                         │
│  │   ├─ geometry (geometry, type=Polygon, SRID=4326)                         │
│  │   ├─ lithology_class (text: ultramafic, mafic, sedimentary)               │
│  │   ├─ age_range (text: e.g., "Proterozoic-Archaean")                       │
│  │   ├─ source (text: "Macrostrat" or "GLiM")                                │
│  │   └─ confidence (numeric: 0.0-1.0)                                        │
│  │   Index: GIST(geometry)                                                   │
│  │                                                                           │
│  ├─ public.heatflow_points                                                   │
│  │   ├─ id (UUID, primary key)                                               │
│  │   ├─ basin_id (UUID, foreign key)                                         │
│  │   ├─ geometry (geometry, type=Point, SRID=4326)                           │
│  │   ├─ heatflow_mwm2 (numeric: mW/m²)                                       │
│  │   ├─ measurement_date (date)                                              │
│  │   ├─ confidence (numeric: 0.0-1.0)                                        │
│  │   └─ source_id (text: "IHFC" identifier)                                  │
│  │   Index: GIST(geometry)                                                   │
│  │                                                                           │
│  RASTER METADATA TABLES                                                      │
│  ├─ public.gravity_tiles                                                     │
│  │   ├─ id (UUID)                                                            │
│  │   ├─ basin_id (UUID)                                                      │
│  │   ├─ raster_path (text: "s3://bucket/curated/gravity/*.tif")              │
│  │   ├─ resolution (text: "~5 km")                                           │
│  │   ├─ bounds (geometry: bounding box)                                      │
│  │   └─ created_at (timestamp)                                               │
│  │                                                                           │
│  └─ public.magnetic_tiles                                                    │
│      ├─ id (UUID)                                                            │
│      ├─ basin_id (UUID)                                                      │
│      ├─ raster_path (text)                                                   │
│      ├─ resolution (text: "2-arc-minute")                                    │
│      ├─ bounds (geometry)                                                    │
│      └─ created_at (timestamp)                                               │
│                                                                              │
│  STATUS: ✅ Indexed, Queryable, Ready for Analysis                          │
│  Query Example:                                                              │
│  SELECT ST_Intersects(geometry, ST_Buffer(ST_Point(-95.5, 38.5), 0.1))      │
│  FROM faults WHERE basin_id = '11e757b7-...' LIMIT 10;                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

        ↓ GENERATE TILES & REPORTS

┌─────────────────────────────────────────────────────────────────────────────┐
│               STAGE 6: TILES & REPORTS (FUTURE PHASES)                       │
│                                                                              │
│  VECTOR TILES (pg_tileserv, Phase 2)                                         │
│  ├─ /data/tiles/vector/faults.pbf (protocol buffer)                          │
│  ├─ /data/tiles/vector/geology.pbf                                           │
│  ├─ /data/tiles/vector/heatflow.pbf                                          │
│  └─ Web endpoint: /data/{layer}/{z}/{x}/{y}.pbf                              │
│                                                                              │
│  RASTER TILES (Cloud Storage, Phase 2)                                       │
│  ├─ /data/tiles/raster/gravity/ (pre-tiled COG)                              │
│  ├─ /data/tiles/raster/magnetic/                                             │
│  └─ /data/tiles/raster/dem/                                                  │
│                                                                              │
│  REPORTS                                                                     │
│  ├─ /data/reports/pipeline_report_*.json (QA results)                        │
│  ├─ /data/reports/data_quality_*.html (visual dashboard)                     │
│  ├─ /data/reports/lineage_*.json (data provenance)                           │
│  └─ /data/reports/summary_*.txt (human-readable summary)                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

        ↓ USE IN ANALYSIS ENGINE

┌─────────────────────────────────────────────────────────────────────────────┐
│         MantleIQ Analysis Engine (Scoring + ML)                              │
│                                                                              │
│  ✓ Fault density calculations (ST_Intersects)                                │
│  ✓ Gravity anomaly overlays (spatial joins)                                  │
│  ✓ Lithology proximity scoring (distance functions)                          │
│  ✓ Heat flow interpolation (IDW from points)                                 │
│  ✓ XGBoost model training (feature generation)                               │
│  ✓ Prospectivity scoring (ensemble method)                                   │
│  ✓ DBSCAN clustering (zone identification)                                   │
│  ✓ SHAP attribution (Phase B)                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Step-by-Step Workflow

### **Step 1: Download**
```bash
# All data sources downloaded to /data/raw/
# Preserves original format, CRS, attributes
# Log files capture: file size, feature count, source URL, timestamp

Download Geology from Macrostrat API
  ├─ Query: /api/v2/units?bbox={basin_bounds}
  ├─ Format: GeoJSON
  ├─ Output: /data/raw/geology/geology_macrostrat.geojson
  └─ Log: Downloaded 245 units, ~25MB, at 2026-05-12 10:15:30

Download Faults from USGS
  ├─ Source: USGS Earthquake Hazards shapefile
  ├─ Format: Shapefile (.shp/.dbf/.shx)
  ├─ Output: /data/raw/faults/faults_usgs.zip
  └─ Log: Downloaded, ~45MB

...similar for gravity, magnetic, heatflow, dem
```

### **Step 2: Normalize**
```bash
# Each file processed individually:

Normalize Geology
  ├─ Read: /data/raw/geology/geology_macrostrat.geojson
  ├─ Validate: 245 features, all valid
  ├─ Check CRS: GeoJSON (EPSG:4326) ✓ already correct
  ├─ Check Attributes: lithology_class ✓, age_range ✓
  ├─ Write: /data/curated/geology/geology_macrostrat_normalized.geojson
  └─ Status: ✓ Complete, 245 features

Normalize Faults
  ├─ Read: /data/raw/faults/faults_usgs.shp (NAD83)
  ├─ Validate: 89 features, 2 invalid
  ├─ Fix: Apply buffer(0) to invalid geometries
  ├─ Reproject: NAD83 → EPSG:4326
  ├─ Check Attributes: fault_name ✓, activity_class ✓
  ├─ Write: /data/curated/faults/faults_usgs_normalized.geojson
  └─ Status: ✓ Complete, 89 features (fixed)

Normalize Gravity Raster
  ├─ Read: /data/raw/gravity/gravity_noaa.tif (irregular projection)
  ├─ Reproject: Custom → EPSG:4326 (bilinear)
  ├─ Convert: COG format with LZW compression, 512×512 tiles
  ├─ Write: /data/curated/gravity/gravity_noaa_normalized.tif
  └─ Status: ✓ Complete, 5km resolution
```

### **Step 3: Validate**
```bash
# Quality assurance on all curated files:

Validate Geology
  ├─ CRS Check: EPSG:4326 ✓
  ├─ Geometry: 245/245 valid ✓
  ├─ Spatial Extent: Within basin bounds ✓
  ├─ Attributes: All required fields present ✓
  └─ Quality Score: 100%

Validate Faults
  ├─ CRS Check: EPSG:4326 ✓
  ├─ Geometry: 89/89 valid ✓ (fixed from 87)
  ├─ Attributes: All required ✓
  └─ Quality Score: 95% (2 were fixed)

Validate Gravity
  ├─ CRS Check: EPSG:4326 ✓
  ├─ Format: Cloud Optimized GeoTIFF ✓
  ├─ Tiling: 512×512 blocks ✓
  ├─ Compression: LZW ✓
  └─ Quality Score: 100%
```

### **Step 4: Load to Database**
```bash
# Insert into PostGIS:

Load Geology
  SQL: INSERT INTO geologic_units (id, basin_id, geometry, lithology_class, age_range, ...)
       SELECT * FROM '/data/curated/geology/geology_macrostrat_normalized.geojson'
  ├─ Rows Inserted: 245
  ├─ Spatial Index: Created on geometry
  ├─ Time: ~2.5 seconds
  └─ Status: ✓ Complete

Load Faults
  SQL: INSERT INTO faults (id, basin_id, geometry, fault_name, activity_class, ...)
  ├─ Rows Inserted: 89
  ├─ Spatial Index: Created
  ├─ Time: ~1.8 seconds
  └─ Status: ✓ Complete

Load Heat Flow Points
  SQL: INSERT INTO heatflow_points (id, basin_id, geometry, heatflow_mwm2, ...)
  ├─ Rows Inserted: 1,234
  ├─ Spatial Index: Created
  ├─ Time: ~3.2 seconds
  └─ Status: ✓ Complete
```

### **Step 5: Generate Report**
```json
{
  "pipeline_execution": {
    "timestamp": "2026-05-12T10:30:00",
    "basin_id": "11e757b7-ddde-48dc-8c7a-619cfa350930",
    "basin_name": "Kansas Rift",
    "duration_minutes": 8.5,
    "status": "SUCCESS",
    "summary": {
      "files_downloaded": 6,
      "files_normalized": 6,
      "files_validated": 6,
      "records_loaded": 1568,
      "quality_score": 97.5
    },
    "details": {
      "geology": {
        "download_size": "25 MB",
        "features": 245,
        "normalized_size": "2.8 MB",
        "validation": "PASS (100%)",
        "database_rows": 245
      },
      "faults": {
        "download_size": "45 MB",
        "features": 89,
        "normalized_size": "4.2 MB",
        "validation": "PASS (95%)",
        "database_rows": 89
      },
      ...similar for other data types
    }
  }
}
```

## 📋 Data Type Details

### **Faults (Vector)**
- **Download:** USGS Earthquake Hazards (.zip with shapefiles)
- **Normalize:** NAD83 → EPSG:4326, fix invalid geometries
- **Curate:** GeoJSON with attributes (fault_name, activity_class, confidence)
- **Load:** `public.faults` table with LineString geometry
- **Queries:** Intersection density, proximity scoring

### **Geology (Vector)**
- **Download:** Macrostrat API GeoJSON (already EPSG:4326)
- **Normalize:** Validate geometries, ensure attributes
- **Curate:** Consistent GeoJSON format
- **Load:** `public.geologic_units` with lithology_class field
- **Queries:** Ultramafic proximity, lithology classification

### **Gravity (Raster)**
- **Download:** NOAA GeoTIFF (mixed CRS, full global extent)
- **Normalize:** Clip to basin bounds, reproject to EPSG:4326
- **Curate:** Cloud Optimized GeoTIFF with 512×512 tiles
- **Load:** Metadata in `public.gravity_tiles`, actual raster in Cloud Storage
- **Queries:** Anomaly overlays, gradient analysis

### **Magnetic (Raster)**
- **Download:** NOAA EMAG2 v3 GeoTIFF (2-arc-minute global)
- **Normalize:** Basin clip, reproject to EPSG:4326, tile to COG
- **Curate:** Cloud Optimized GeoTIFF
- **Load:** Metadata in `public.magnetic_tiles`
- **Queries:** Anomaly analysis, structural interpretation

### **Heat Flow (Point)**
- **Download:** IHFC CSV (lat, lon, mW/m² columns)
- **Normalize:** Convert to GeoDataFrame, ensure EPSG:4326
- **Curate:** GeoJSON with Point geometries
- **Load:** `public.heatflow_points` with numeric heat flow values
- **Queries:** Interpolation, thermal gradient analysis

## 🎯 Key Metrics

| Step | Input | Output | Time | Status |
|------|-------|--------|------|--------|
| **Download** | URLs | 6 files, ~140 MB | 15-20 min | Manual (Phase 1) |
| **Normalize** | Raw files | Standardized, EPSG:4326 | 5-10 min | Automated (Phase 2) |
| **Validate** | Normalized files | Quality report | 2-3 min | Automated (Phase 2) |
| **Load** | Curated files | 1,500+ DB records | 8-15 sec | Automated |
| **Total** | Public sources | Production database | ~25-35 min | Ready |

## 🚀 Getting Started

```bash
# 1. Clone repository (done)
cd /Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp

# 2. Start data pipeline
bash /data/QUICK_START.sh

# 3. Select "Run full pipeline" to download → normalize → load

# 4. Check reports
cat /data/reports/pipeline_report_*.json

# 5. Query database
psql -h db.supabase.co -U postgres -d postgres \
  -c "SELECT count(*) FROM geologic_units WHERE basin_id = '11e757b7-...'"
```

## 📚 Documentation Structure

- **[DATA_PIPELINE_README.md](DATA_PIPELINE_README.md)** — Comprehensive guide
- **[WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md)** — This file (architecture + workflow)
- **[QUICK_START.sh](QUICK_START.sh)** — Interactive CLI tool
- **[data_pipeline.py](../backend/scripts/data_pipeline.py)** — Implementation

---

**Version:** 1.0  
**Updated:** 2026-05-12  
**Status:** Production Ready
