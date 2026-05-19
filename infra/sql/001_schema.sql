-- MantleIQ Database Schema
-- PostgreSQL 15 + PostGIS 3.4
-- Normalized to EPSG:4326 (WGS84)

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. BASINS (Study areas)
-- ============================================================================
CREATE TABLE IF NOT EXISTS basins (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL UNIQUE,
  region TEXT,
  country TEXT,
  geometry GEOMETRY(POLYGON, 4326),
  data_coverage_score FLOAT,
  description TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_basins_geom ON basins USING GIST(geometry);
CREATE INDEX idx_basins_name ON basins(name);

-- ============================================================================
-- 2. DATA LAYERS METADATA REGISTRY
-- ============================================================================
CREATE TABLE IF NOT EXISTS data_layers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  basin_id UUID REFERENCES basins(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  source_name TEXT,
  source_url TEXT,
  layer_type TEXT NOT NULL, -- 'vector', 'raster', 'point'
  raw_uri TEXT, -- S3/GCS path to raw data
  curated_uri TEXT, -- S3/GCS path to processed data
  target_table TEXT,
  license TEXT,
  resolution TEXT,
  acquisition_date DATE,
  coverage_geometry GEOMETRY(POLYGON, 4326),
  source_confidence FLOAT DEFAULT 0.8,
  data_quality FLOAT DEFAULT 0.8,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_data_layers_basin ON data_layers(basin_id);
CREATE INDEX idx_data_layers_type ON data_layers(layer_type);
CREATE INDEX idx_data_layers_table ON data_layers(target_table);

-- ============================================================================
-- 3. GEOLOGIC UNITS / LITHOLOGY
-- ============================================================================
CREATE TABLE IF NOT EXISTS geologic_units (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  basin_id UUID REFERENCES basins(id) ON DELETE CASCADE,
  source TEXT,
  source_unit_id TEXT,
  lithology_raw TEXT,
  lithology_class TEXT, -- 'ultramafic', 'mafic', 'sedimentary', 'caprock', 'basement'
  age_min_ma FLOAT, -- Minimum age (Million years ago)
  age_max_ma FLOAT, -- Maximum age
  confidence FLOAT DEFAULT 0.8,
  geometry GEOMETRY(MULTIPOLYGON, 4326),

  -- Derived classifications
  ultramafic_fraction FLOAT DEFAULT 0.0,
  mafic_fraction FLOAT DEFAULT 0.0,
  sedimentary_fraction FLOAT DEFAULT 0.0,
  fine_clastic_fraction FLOAT DEFAULT 0.0,
  carbonate_fraction FLOAT DEFAULT 0.0,
  evaporite_fraction FLOAT DEFAULT 0.0,
  basement_cover_contact_distance_km FLOAT,

  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_geologic_units_geom ON geologic_units USING GIST(geometry);
CREATE INDEX idx_geologic_units_basin ON geologic_units(basin_id);
CREATE INDEX idx_geologic_units_lithology_class ON geologic_units(lithology_class);

-- ============================================================================
-- 4. STRUCTURAL FEATURES / FAULTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS faults (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  basin_id UUID REFERENCES basins(id) ON DELETE CASCADE,
  source TEXT,
  fault_name TEXT,
  fault_type TEXT, -- 'normal', 'reverse', 'strike-slip', 'unknown'
  activity_class TEXT, -- 'active', 'quaternary', 'mapped', 'inferred'
  confidence FLOAT DEFAULT 0.8,
  geometry GEOMETRY(MULTILINESTRING, 4326),

  -- Derived attributes
  fault_density_km_per_km2 FLOAT,
  fault_intersection_density FLOAT,
  distance_to_nearest_major_fault_km FLOAT,
  lineament_density_proxy FLOAT,
  structural_complexity_index FLOAT,

  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_faults_geom ON faults USING GIST(geometry);
CREATE INDEX idx_faults_basin ON faults(basin_id);
CREATE INDEX idx_faults_activity ON faults(activity_class);

-- ============================================================================
-- 5. ANALYSIS GRID CELLS (H3 or square grid)
-- ============================================================================
CREATE TABLE IF NOT EXISTS grid_cells (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  basin_id UUID NOT NULL REFERENCES basins(id) ON DELETE CASCADE,
  h3_id TEXT, -- H3 index identifier (if using H3 grid)
  grid_x INT, -- Grid X coordinate (if using square grid)
  grid_y INT, -- Grid Y coordinate (if using square grid)
  geometry GEOMETRY(POLYGON, 4326),
  centroid GEOMETRY(POINT, 4326),
  lat FLOAT,
  lon FLOAT,
  area_km2 FLOAT,
  data_completeness FLOAT DEFAULT 0.0,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_grid_cells_geom ON grid_cells USING GIST(geometry);
CREATE INDEX idx_grid_cells_basin ON grid_cells(basin_id);
CREATE INDEX idx_grid_cells_h3 ON grid_cells(h3_id) WHERE h3_id IS NOT NULL;
CREATE INDEX idx_grid_cells_centroid_geom ON grid_cells USING GIST(centroid);

-- ============================================================================
-- 6. COMPUTED FEATURES (30+ spatial metrics per cell)
-- ============================================================================
CREATE TABLE IF NOT EXISTS features (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  grid_cell_id UUID NOT NULL REFERENCES grid_cells(id) ON DELETE CASCADE,
  basin_id UUID NOT NULL REFERENCES basins(id) ON DELETE CASCADE,
  model_version TEXT DEFAULT 'prospectivity_v1',

  -- Hydrogen Generation (30%)
  ultramafic_fraction FLOAT,
  mafic_fraction FLOAT,
  serpentinization_proxy FLOAT,
  magnetic_anomaly_score FLOAT,
  heatflow_score FLOAT,

  -- Fluid Interaction (20%)
  groundwater_proxy FLOAT,
  permeability_proxy FLOAT,
  slope_flow_proxy FLOAT,
  basin_presence_score FLOAT,

  -- Structural Pathways (20%)
  fault_density_score FLOAT,
  fault_intersection_score FLOAT,
  gravity_gradient_score FLOAT,
  magnetic_gradient_score FLOAT,
  structural_complexity_score FLOAT,

  -- Trap & Retention (15%)
  sedimentary_cover_score FLOAT,
  caprock_proxy_score FLOAT,
  basin_margin_score FLOAT,
  closure_proxy_score FLOAT,
  porosity_proxy_score FLOAT,
  breach_risk_penalty FLOAT,

  -- Surface Indicators (10%)
  h2_seep_score FLOAT,
  gas_anomaly_score FLOAT,
  helium_analog_score FLOAT,
  microbial_signature_score FLOAT,

  -- Thermodynamic (5%)
  thermal_window_score FLOAT,
  reaction_viability_score FLOAT,

  -- Data Quality
  data_coverage FLOAT,
  data_quality FLOAT,
  missing_data_completeness FLOAT,
  confidence_modifier FLOAT,

  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_features_cell ON features(grid_cell_id);
CREATE INDEX idx_features_basin ON features(basin_id);
CREATE INDEX idx_features_model_version ON features(model_version);

-- ============================================================================
-- 7. MODEL OUTPUTS (Scoring results)
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_outputs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  grid_cell_id UUID NOT NULL REFERENCES grid_cells(id) ON DELETE CASCADE,
  basin_id UUID NOT NULL REFERENCES basins(id) ON DELETE CASCADE,
  model_version TEXT DEFAULT 'prospectivity_v1',

  -- Component Scores (0-100)
  f_generation FLOAT,
  f_fluid_interaction FLOAT,
  f_structural_pathways FLOAT,
  f_trap_retention FLOAT,
  f_surface_indicators FLOAT,
  f_thermodynamic FLOAT,

  -- Final Score
  rule_score FLOAT,
  ml_score FLOAT,
  ensemble_score FLOAT,
  confidence_score FLOAT,
  final_score FLOAT,

  -- Ranking
  rank_global INTEGER,
  rank_basin INTEGER,
  score_class TEXT, -- 'high_priority', 'strong_prospect', 'moderate', 'weak', 'low'

  -- Attribution
  feature_importance JSONB,
  top_drivers JSONB,
  missing_data_layers JSONB,

  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_model_outputs_cell ON model_outputs(grid_cell_id);
CREATE INDEX idx_model_outputs_basin ON model_outputs(basin_id);
CREATE INDEX idx_model_outputs_final_score ON model_outputs(final_score DESC);
CREATE INDEX idx_model_outputs_rank_basin ON model_outputs(basin_id, rank_basin);

-- ============================================================================
-- 8. PROSPECT ZONES (Clustered cells)
-- ============================================================================
CREATE TABLE IF NOT EXISTS zones (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  basin_id UUID NOT NULL REFERENCES basins(id) ON DELETE CASCADE,
  model_version TEXT DEFAULT 'prospectivity_v1',

  name TEXT NOT NULL,
  geometry GEOMETRY(POLYGON, 4326),
  centroid GEOMETRY(POINT, 4326),

  -- Aggregated Scores
  prospectivity_score FLOAT,
  confidence_score FLOAT,
  rank INTEGER,

  -- Zone Properties
  cell_count INTEGER,
  area_km2 FLOAT,
  top_features JSONB,
  explanation_summary TEXT,
  recommended_next_actions JSONB,

  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_zones_geom ON zones USING GIST(geometry);
CREATE INDEX idx_zones_basin ON zones(basin_id);
CREATE INDEX idx_zones_rank ON zones(rank);
CREATE INDEX idx_zones_prospectivity_score ON zones(prospectivity_score DESC);

-- ============================================================================
-- 9. SURFACE INDICATORS (H2 seeps, gas anomalies, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS surface_indicators (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  basin_id UUID REFERENCES basins(id) ON DELETE CASCADE,

  source TEXT,
  indicator_type TEXT, -- 'known_h2_seep', 'gas_show', 'soil_h2_anomaly', 'helium_anomaly', 'hydrothermal_indicator'

  -- Geochemistry
  h2_percent FLOAT,
  helium_ppm FLOAT,
  methane_percent FLOAT,
  measurement_method TEXT,
  sample_date DATE,

  confidence FLOAT DEFAULT 0.8,
  geometry GEOMETRY(POINT, 4326),

  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_surface_indicators_geom ON surface_indicators USING GIST(geometry);
CREATE INDEX idx_surface_indicators_basin ON surface_indicators(basin_id);
CREATE INDEX idx_surface_indicators_type ON surface_indicators(indicator_type);

-- ============================================================================
-- 10. REPORTS (PDF exports and analysis summaries)
-- ============================================================================
CREATE TABLE IF NOT EXISTS reports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  basin_id UUID REFERENCES basins(id) ON DELETE CASCADE,
  zone_id UUID REFERENCES zones(id) ON DELETE CASCADE,

  report_type TEXT, -- 'zone_brief', 'basin_summary', 'comparison'
  file_path TEXT, -- S3/GCS URI
  summary_json JSONB,

  generated_by TEXT,
  generated_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP
);

CREATE INDEX idx_reports_basin ON reports(basin_id);
CREATE INDEX idx_reports_zone ON reports(zone_id);
CREATE INDEX idx_reports_type ON reports(report_type);

-- ============================================================================
-- 11. THERMAL DATA - Heat Flow Points
-- ============================================================================
CREATE TABLE IF NOT EXISTS heatflow_points (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  basin_id UUID REFERENCES basins(id) ON DELETE CASCADE,

  source TEXT,
  heatflow_mwm2 FLOAT,
  measurement_type TEXT,
  quality_code TEXT,

  geometry GEOMETRY(POINT, 4326),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_heatflow_points_geom ON heatflow_points USING GIST(geometry);
CREATE INDEX idx_heatflow_points_basin ON heatflow_points(basin_id);

-- ============================================================================
-- 12. RASTER METADATA REGISTRY
-- ============================================================================
CREATE TABLE IF NOT EXISTS raster_metadata (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  data_layer_id UUID REFERENCES data_layers(id),

  source TEXT,
  raster_uri TEXT, -- Cloud Optimized GeoTIFF path
  resolution TEXT,
  bbox GEOMETRY(POLYGON, 4326),
  confidence FLOAT DEFAULT 0.8,

  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_raster_metadata_bbox ON raster_metadata USING GIST(bbox);

-- ============================================================================
-- 13. ANALYSIS JOBS (Async processing tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS analysis_jobs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  basin_id UUID NOT NULL REFERENCES basins(id) ON DELETE CASCADE,

  job_type TEXT, -- 'full_analysis', 'incremental_update', 'export'
  status TEXT DEFAULT 'queued', -- 'queued', 'running', 'completed', 'failed'

  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  error_message TEXT,

  result_metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analysis_jobs_basin ON analysis_jobs(basin_id);
CREATE INDEX idx_analysis_jobs_status ON analysis_jobs(status);

-- ============================================================================
-- 14. AUDIT LOG
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  table_name TEXT,
  record_id UUID,
  action TEXT, -- 'INSERT', 'UPDATE', 'DELETE'
  changed_fields JSONB,
  changed_by TEXT,
  changed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_changed_at ON audit_log(changed_at);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Top-scoring zones per basin
CREATE OR REPLACE VIEW v_top_zones AS
SELECT
  z.id,
  z.basin_id,
  z.name,
  z.prospectivity_score,
  z.confidence_score,
  z.rank,
  b.name AS basin_name,
  z.cell_count,
  z.area_km2
FROM zones z
JOIN basins b ON z.basin_id = b.id
WHERE z.rank <= 20
ORDER BY z.basin_id, z.rank;

-- Data completeness summary per basin
CREATE OR REPLACE VIEW v_data_completeness AS
SELECT
  b.id,
  b.name,
  COUNT(DISTINCT dl.id) AS total_layers,
  COUNT(DISTINCT CASE WHEN dl.curated_uri IS NOT NULL THEN dl.id END) AS available_layers,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN dl.curated_uri IS NOT NULL THEN dl.id END) /
        NULLIF(COUNT(DISTINCT dl.id), 0), 1) AS coverage_percent
FROM basins b
LEFT JOIN data_layers dl ON b.id = dl.basin_id
GROUP BY b.id, b.name;

-- Scoring summary per zone
CREATE OR REPLACE VIEW v_zone_details AS
SELECT
  z.id,
  z.basin_id,
  z.name,
  z.prospectivity_score,
  z.confidence_score,
  z.rank,
  z.top_features,
  z.explanation_summary,
  z.recommended_next_actions,
  ST_AsGeoJSON(z.geometry) AS geometry_geojson,
  ST_X(z.centroid) AS lon,
  ST_Y(z.centroid) AS lat
FROM zones z
ORDER BY z.basin_id, z.rank;

-- ============================================================================
-- COMMENTS (Documentation)
-- ============================================================================
COMMENT ON TABLE basins IS 'Study area boundaries (sedimentary basins, exploration regions)';
COMMENT ON TABLE grid_cells IS 'Regular analysis grid (H3 or square) for cell-level prospectivity scoring';
COMMENT ON TABLE features IS 'Computed geospatial features (30+ metrics) per grid cell';
COMMENT ON TABLE model_outputs IS 'Scoring results: rule, ML, ensemble, confidence, final score, rank';
COMMENT ON TABLE zones IS 'Clustered prospect zones (aggregated from grid cells) with rankings';
COMMENT ON TABLE surface_indicators IS 'Known hydrogen seeps, gas shows, helium anomalies, soil gas surveys';
COMMENT ON COLUMN zones.prospectivity_score IS 'Confidence-adjusted final score (0-100)';
COMMENT ON COLUMN zones.confidence_score IS 'Confidence modifier (0.5-1.0) based on data completeness';

-- ============================================================================
-- FINAL SETUP
-- ============================================================================

-- Note: VACUUM ANALYZE cannot run in transaction block (Supabase SQL Editor limitation)
-- Run manually after schema creation if needed: VACUUM ANALYZE;
-- VACUUM ANALYZE;

-- Log schema creation
INSERT INTO audit_log (table_name, action, changed_by, changed_at)
VALUES ('schema', 'CREATE', 'mantleiq_init', NOW())
ON CONFLICT DO NOTHING;

-- Schema version
CREATE TABLE IF NOT EXISTS schema_version (
  version_id INT PRIMARY KEY,
  schema_name TEXT,
  installed_on TIMESTAMP DEFAULT NOW(),
  description TEXT
);

INSERT INTO schema_version (version_id, schema_name, description)
VALUES (1, 'mantleiq', 'Initial MantleIQ schema with PostGIS, zones, features, scoring')
ON CONFLICT DO NOTHING;
