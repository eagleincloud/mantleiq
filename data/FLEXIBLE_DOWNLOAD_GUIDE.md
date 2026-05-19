# MantleIQ Flexible Data Pipeline - Download Guide

**Problem Solved:** Download data with OR without bounding box filtering, re-download regions, select from multiple basins

---

## 🎯 Key Features

### ✅ No Bounding Box Required
- Download full global datasets without geographic filtering
- All data in `/data/raw/geology_macrostrat_global.geojson`
- No region selection needed

### ✅ Multiple Pre-defined Basins
Choose from existing basins with known bounds:
- Kansas Rift Basin
- Permian Basin
- Illinois Basin
- Gulf Coast Basin
- OR Global (no filter)

### ✅ Re-download Same Region
Download the same region multiple times:
- First download creates file
- Second download skips (file exists)
- Use `force_redownload=True` to overwrite

### ✅ Custom Basin Support
Add your own basin bounds easily

---

## 📍 Available Basins

```
KANSAS RIFT BASIN
├─ Bounds: -98°W to -93°W, 37°N to 40°N
├─ Description: Central US natural hydrogen prospectivity
└─ Files: geology_macrostrat_kansas_rift.geojson, faults_usgs_kansas_rift.zip, etc.

PERMIAN BASIN
├─ Bounds: -104°W to -98°W, 30°N to 36°N
├─ Description: Texas-New Mexico natural hydrogen system
└─ Files: geology_macrostrat_permian.geojson, faults_usgs_permian.zip, etc.

ILLINOIS BASIN
├─ Bounds: -92°W to -87°W, 36°N to 42°N
├─ Description: Midwestern US sedimentary system
└─ Files: geology_macrostrat_illinois.geojson, faults_usgs_illinois.zip, etc.

GULF COAST BASIN
├─ Bounds: -97°W to -88°W, 25°N to 30°N
├─ Description: Gulf of Mexico coastal hydrogen province
└─ Files: geology_macrostrat_gulf_coast.geojson, faults_usgs_gulf_coast.zip, etc.

GLOBAL (NO FILTER)
├─ Bounds: NONE - Downloads full datasets
├─ Description: Complete global geospatial data
└─ Files: geology_macrostrat_global.geojson, gravity_noaa_global.tif, etc.
```

---

## 🚀 How to Use

### **Option 1: Interactive Menu** (Recommended)
```bash
python3 /Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend/scripts/data_pipeline_flexible.py

# Output:
# AVAILABLE BASINS/REGIONS
# KANSAS_RIFT: Central US...
# PERMIAN: Texas-New Mexico...
# ...GLOBAL: No filter...
#
# SELECT OPTION:
# 1) Download for Kansas Rift (with bounds)
# 2) Download for Permian Basin (with bounds)
# 3) Download for Illinois Basin (with bounds)
# 4) Download GLOBAL (no bounds, full datasets)
# 5) Re-download same region (force overwrite)
# 6) Exit
#
# Enter choice (1-6): 4
```

### **Option 2: Download Kansas Rift (with bounds)**
```python
import sys
sys.path.insert(0, '/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend')
from scripts.data_pipeline_flexible import FlexibleDataPipeline

# Create pipeline for Kansas Rift with bounds
pipeline = FlexibleDataPipeline(
    basin_name='kansas_rift',
    use_bounds=True  # Apply geographic filter
)

pipeline.run_pipeline()

# Files created:
# /data/raw/geology/geology_macrostrat_kansas_rift.geojson
# /data/raw/faults/faults_usgs_kansas_rift.zip
# etc.
```

### **Option 3: Download Global (no bounds)**
```python
import sys
sys.path.insert(0, '/Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/backend')
from scripts.data_pipeline_flexible import FlexibleDataPipeline

# Create pipeline for GLOBAL without bounds
pipeline = FlexibleDataPipeline(
    basin_name='global',
    use_bounds=False  # No geographic filtering
)

pipeline.run_pipeline()

# Files created:
# /data/raw/geology/geology_macrostrat_global.geojson (FULL DATASET)
# /data/raw/gravity/gravity_noaa_global.tif (FULL GLOBAL GRID)
# /data/raw/magnetic/magnetic_emag2_global.tif (FULL GLOBAL GRID)
# etc.
```

### **Option 4: Download Permian Basin**
```python
from scripts.data_pipeline_flexible import FlexibleDataPipeline

pipeline = FlexibleDataPipeline(basin_name='permian', use_bounds=True)
pipeline.run_pipeline()

# Files created:
# /data/raw/geology/geology_macrostrat_permian.geojson
# /data/raw/gravity/gravity_noaa_permian.tif
# etc.
```

### **Option 5: Re-download Same Region (Force Overwrite)**
```python
from scripts.data_pipeline_flexible import FlexibleDataPipeline

# First download
pipeline = FlexibleDataPipeline(basin_name='kansas_rift')
pipeline.run_pipeline()
# Files created ✓

# Later, download again (overwrites)
pipeline = FlexibleDataPipeline(basin_name='kansas_rift')
pipeline.run_pipeline(force_redownload=True)
# Files overwritten with latest data ✓
```

---

## 🔄 Understanding File Naming

### **With Bounds (Regional)**
```
geology_macrostrat_kansas_rift.geojson    ← Regional subset
geology_macrostrat_permian.geojson        ← Different region
geology_macrostrat_illinois.geojson       ← Another region
```

### **Without Bounds (Global)**
```
geology_macrostrat_global.geojson         ← Full global dataset
gravity_noaa_global.tif                   ← Full global raster
magnetic_emag2_global.tif                 ← Full global raster
```

Each basin gets its own files to avoid conflicts when comparing regions!

---

## 📊 Workflow: First Download vs. Re-download

### **First Download**
```
User selects: Kansas Rift Basin
│
└─ Pipeline creates:
   ├─ /data/raw/geology/geology_macrostrat_kansas_rift.geojson
   ├─ /data/raw/faults/faults_usgs_kansas_rift.zip
   ├─ /data/raw/gravity/gravity_noaa_kansas_rift.tif
   └─ /data/raw/magnetic/magnetic_emag2_kansas_rift.tif
   
Status: ✓ Files downloaded
```

### **Later: Re-download Same Region**
```
User selects: Kansas Rift Basin again (with force_redownload=True)
│
├─ Check: File exists? YES
├─ Action: force_redownload=True? YES
└─ Result: Overwrite with latest data
   
Status: ✓ Files updated
```

### **No Re-download (Default Behavior)**
```
User selects: Kansas Rift Basin again (with force_redownload=False)
│
├─ Check: File exists? YES
├─ Action: Skip download
└─ Message: "⚠ File exists: ... (Use force_redownload=True to overwrite)"
   
Status: ✓ Existing files preserved
```

---

## ✨ No Bounding Box Example

### **Old Approach (With Bounds)**
```python
kansas_bounds = (-98.0, 37.0, -93.0, 40.0)
pipeline.download_geology(kansas_bounds)
# Returns: 245 features (only Kansas Rift)
```

### **New Approach (No Bounds)**
```python
pipeline = FlexibleDataPipeline(basin_name='global', use_bounds=False)
pipeline.download_geology()
# Returns: 50,000+ features (ENTIRE MACROSTRAT DATABASE)
```

**Benefit:** You get complete data, can filter in PostGIS later if needed!

---

## 🛠️ Adding Your Own Basin

### **Step 1: Define Basin in Script**
```python
BASINS = {
    # ... existing basins ...
    'my_custom_basin': {
        'name': 'My Custom Basin Name',
        'bounds': (-100.0, 35.0, -95.0, 40.0),  # (west, south, east, north)
        'description': 'Description of this basin'
    }
}
```

### **Step 2: Use It**
```python
pipeline = FlexibleDataPipeline(basin_name='my_custom_basin', use_bounds=True)
pipeline.run_pipeline()

# Files created:
# /data/raw/geology/geology_macrostrat_my_custom_basin.geojson
# /data/raw/faults/faults_usgs_my_custom_basin.zip
# etc.
```

---

## 📋 Comparison: Bounds vs. No Bounds

| Aspect | With Bounds (Regional) | Without Bounds (Global) |
|--------|------------------------|------------------------|
| **Data Volume** | Smaller (region clip) | Larger (full dataset) |
| **Download Time** | Faster (~5-10 min) | Slower (~20-30 min) |
| **File Size** | ~50-100 MB | ~500+ MB |
| **Use Case** | Focused analysis | Comparative studies |
| **Storage** | Efficient | Requires more space |
| **Re-use** | Per-region files | Single global file |
| **Database** | Loaded quickly | Takes longer to load |
| **Analysis** | Fast queries | Slower queries |

---

## 🎯 Typical Workflows

### **Workflow 1: Compare Multiple Regions**
```python
from scripts.data_pipeline_flexible import FlexibleDataPipeline

regions = ['kansas_rift', 'permian', 'illinois']

for region in regions:
    pipeline = FlexibleDataPipeline(basin_name=region, use_bounds=True)
    pipeline.run_pipeline()
    print(f"✓ Downloaded {region}")

# Result: 3 separate region folders with region-specific data
# /data/raw/geology/
#   ├─ geology_macrostrat_kansas_rift.geojson
#   ├─ geology_macrostrat_permian.geojson
#   └─ geology_macrostrat_illinois.geojson
```

### **Workflow 2: Get Global Baseline, Then Regional Focus**
```python
# First: Download global for reference
pipeline = FlexibleDataPipeline(basin_name='global', use_bounds=False)
pipeline.run_pipeline()
print("✓ Global baseline data downloaded")

# Later: Analyze specific region
pipeline = FlexibleDataPipeline(basin_name='kansas_rift', use_bounds=True)
pipeline.run_pipeline()
print("✓ Kansas Rift regional data downloaded")

# Result: Both global and regional data available for comparison
```

### **Workflow 3: Update Data**
```python
# Initial download
pipeline = FlexibleDataPipeline(basin_name='kansas_rift')
pipeline.run_pipeline()

# ... (6 months later) ...

# Re-download latest data
pipeline = FlexibleDataPipeline(basin_name='kansas_rift')
pipeline.run_pipeline(force_redownload=True)
print("✓ Data updated with latest sources")
```

---

## 🔍 Checking Downloaded Files

### **See All Downloaded Data**
```bash
# List all raw files
find /Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/data/raw -type f

# List by type
ls /Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/data/raw/geology/
# Output:
# geology_macrostrat_kansas_rift.geojson
# geology_macrostrat_permian.geojson
# geology_macrostrat_global.geojson

ls /Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/data/raw/gravity/
# Output:
# gravity_noaa_kansas_rift.tif
# gravity_noaa_global.tif

# Check file sizes
du -sh /Users/adityatiwari/Downloads/MantleIQ/mantleiq-mvp/data/raw/*/*
```

---

## 📝 Pipeline Report

Each run generates a JSON report showing what was downloaded:

```json
{
  "timestamp": "2026-05-12T14:30:00",
  "basin": "kansas_rift",
  "bounds": [-98.0, 37.0, -93.0, 40.0],
  "use_bounds": true,
  "steps": [
    {
      "step": "download_geology",
      "status": "success",
      "file": "/data/raw/geology/geology_macrostrat_kansas_rift.geojson",
      "features": 245
    },
    {
      "step": "download_faults",
      "status": "staged",
      "file": "/data/raw/faults/faults_usgs_kansas_rift.zip",
      "note": "Manual download required"
    }
  ]
}
```

Check reports: `ls /data/reports/pipeline_report_*.json`

---

## ❓ FAQ

### **Q: Can I download Kansas Rift twice?**
**A:** Yes! First download creates file. Second download will:
- Skip by default (file already exists)
- OR overwrite if you use `force_redownload=True`

### **Q: Can I download without bounding box?**
**A:** Yes! Use `basin_name='global'` with `use_bounds=False`. You get complete global datasets.

### **Q: What if I want custom bounds?**
**A:** Add your own basin to the `BASINS` dictionary with custom bounds, then use it.

### **Q: Will downloaded files overwrite?**
**A:** No by default. Each region gets its own files:
- `geology_macrostrat_kansas_rift.geojson` (Kansas)
- `geology_macrostrat_permian.geojson` (Permian)
- `geology_macrostrat_global.geojson` (Global)

### **Q: How much storage for global downloads?**
**A:** ~500-800 MB per data type. Total ~2-3 GB for all data types.

### **Q: Can I download same region multiple times to update?**
**A:** Yes! Use `force_redownload=True` to get latest data and overwrite old files.

### **Q: Which is faster - with bounds or without?**
**A:** With bounds is faster (~5-10 min vs. 20-30 min) because it downloads less data.

---

## 🚀 Quick Commands

```bash
# Interactive menu (easiest)
python3 /backend/scripts/data_pipeline_flexible.py

# Download Kansas Rift (with bounds)
python3 << 'EOF'
from scripts.data_pipeline_flexible import FlexibleDataPipeline
pipeline = FlexibleDataPipeline('kansas_rift', use_bounds=True)
pipeline.run_pipeline()
EOF

# Download Global (no bounds)
python3 << 'EOF'
from scripts.data_pipeline_flexible import FlexibleDataPipeline
pipeline = FlexibleDataPipeline('global', use_bounds=False)
pipeline.run_pipeline()
EOF

# Re-download same region
python3 << 'EOF'
from scripts.data_pipeline_flexible import FlexibleDataPipeline
pipeline = FlexibleDataPipeline('kansas_rift')
pipeline.run_pipeline(force_redownload=True)
EOF

# See available basins
python3 << 'EOF'
from scripts.data_pipeline_flexible import FlexibleDataPipeline
pipeline = FlexibleDataPipeline()
pipeline.list_available_basins()
EOF
```

---

## 🎯 Summary

| Need | Use This | Code |
|------|----------|------|
| Download Kansas Rift (bounds) | Interactive menu | `python3 data_pipeline_flexible.py` |
| Download global (no bounds) | Interactive menu | Option 4 |
| Download Permian | Code | `FlexibleDataPipeline('permian', use_bounds=True)` |
| Download same region again | Code | `.run_pipeline(force_redownload=True)` |
| Add custom region | Edit BASINS dict | Add your bounds to `BASINS` |
| Compare multiple regions | Loop script | `for region in ['kansas', 'permian']` |

---

**Version:** 2.0 (Flexible)  
**Updated:** 2026-05-12  
**Status:** Production Ready  
**Basins:** 5 pre-defined + support for custom
