"""
SQLAlchemy ORM models mapping to PostgreSQL schema.
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class BasinORM(Base):
    """Basins table"""
    __tablename__ = "basins"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    region = Column(String, nullable=True)
    country = Column(String, nullable=True)
    # geometry = Column(Geometry('POLYGON', 4326), nullable=True)  # PostGIS
    data_coverage_score = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DataLayersORM(Base):
    """Data layers metadata registry"""
    __tablename__ = "data_layers"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    basin_id = Column(PGUUID(as_uuid=True), ForeignKey("basins.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False)
    source_name = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    layer_type = Column(String, nullable=False)  # 'vector', 'raster', 'point'
    raw_uri = Column(String, nullable=True)
    curated_uri = Column(String, nullable=True)
    target_table = Column(String, nullable=True)
    license = Column(String, nullable=True)
    resolution = Column(String, nullable=True)
    acquisition_date = Column(DateTime, nullable=True)
    # coverage_geometry = Column(Geometry('POLYGON', 4326), nullable=True)
    source_confidence = Column(Float, default=0.8)
    data_quality = Column(Float, default=0.8)
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class GridCellsORM(Base):
    """Analysis grid cells (supports H3 and Polygon grids)"""
    __tablename__ = "grid_cells"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    basin_id = Column(PGUUID(as_uuid=True), ForeignKey("basins.id", ondelete="CASCADE"))
    h3_id = Column(String, nullable=True)
    grid_index = Column(Integer, nullable=True)
    grid_type = Column(String, default="polygon")  # 'polygon' or 'h3'
    # geometry = Column(Geometry('POLYGON', 4326), nullable=False)
    centroid_lon = Column(Float, nullable=True)
    centroid_lat = Column(Float, nullable=True)
    grid_x = Column(Integer, nullable=True)  # For polygon grids
    grid_y = Column(Integer, nullable=True)  # For polygon grids
    h3_resolution = Column(Integer, nullable=True)  # For H3 grids
    created_at = Column(DateTime, default=datetime.utcnow)


class HydrogenProspectsORM(Base):
    """Natural hydrogen prospects within grid cells"""
    __tablename__ = "hydrogen_prospects"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grid_cell_id = Column(PGUUID(as_uuid=True), ForeignKey("grid_cells.id", ondelete="CASCADE"))
    basin_id = Column(PGUUID(as_uuid=True), ForeignKey("basins.id", ondelete="CASCADE"))
    longitude = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    prospect_type = Column(String, nullable=True)  # 'active_seep', 'geochemical_anomaly', etc.
    significance_score = Column(Float, nullable=True)  # 0-100, independent of grid score
    h3_id = Column(String, nullable=True)  # For H3-specific prospects
    h3_distance_to_center = Column(Integer, nullable=True)  # H3 distance units
    discovered_date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GridConfigurationsORM(Base):
    """Grid configuration metadata for different grid types"""
    __tablename__ = "grid_configurations"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    basin_id = Column(PGUUID(as_uuid=True), ForeignKey("basins.id", ondelete="CASCADE"))
    grid_type = Column(String, nullable=False)  # 'polygon' or 'h3'
    grid_params = Column(JSON, default={})  # {resolution: 5} for H3, {rows: 10, cols: 10} for polygon
    cell_count = Column(Integer, nullable=True)
    prospect_count = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FeaturesORM(Base):
    """Computed geospatial features"""
    __tablename__ = "features"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grid_cell_id = Column(PGUUID(as_uuid=True), ForeignKey("grid_cells.id", ondelete="CASCADE"))
    basin_id = Column(PGUUID(as_uuid=True), ForeignKey("basins.id", ondelete="CASCADE"))

    # 25+ computed features
    fault_density = Column(Float, nullable=True)
    ultramafic_proximity = Column(Float, nullable=True)
    gravity_anomaly = Column(Float, nullable=True)
    magnetic_anomaly = Column(Float, nullable=True)
    heat_flow_indicator = Column(Float, nullable=True)
    structural_complexity = Column(Float, nullable=True)
    seep_proximity = Column(Float, nullable=True)

    # Data quality
    data_coverage = Column(Float, nullable=True)
    data_quality = Column(Float, nullable=True)
    missing_completeness = Column(Float, nullable=True)

    # Metadata
    feature_vector = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ModelOutputsORM(Base):
    """Scoring results"""
    __tablename__ = "model_outputs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(PGUUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"))
    grid_cell_id = Column(PGUUID(as_uuid=True), ForeignKey("grid_cells.id", ondelete="CASCADE"))

    # Scores
    rule_score = Column(Float, nullable=True)
    ml_score = Column(Float, nullable=True)
    ensemble_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)

    # Confidence
    confidence_raw = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # Ranking
    rank = Column(Integer, nullable=True)
    percentile = Column(Integer, nullable=True)

    # Components
    components = Column(JSON, default={})  # {f_generation, f_fluid_interaction, ...}

    # Attribution
    top_features = Column(JSON, default=[])  # List of {name, label, value, weight, contribution}

    # Explanation
    explanation_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ZonesORM(Base):
    """Clustered prospect zones"""
    __tablename__ = "zones"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    basin_id = Column(PGUUID(as_uuid=True), ForeignKey("basins.id", ondelete="CASCADE"))
    name = Column(String, nullable=True)
    # geometry = Column(Geometry('POLYGON', 4326), nullable=False)
    prospectivity_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    cluster_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalysisJobsORM(Base):
    """Async analysis jobs"""
    __tablename__ = "analysis_jobs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    basin_id = Column(PGUUID(as_uuid=True), ForeignKey("basins.id", ondelete="CASCADE"))
    mode = Column(String, default="standard")
    model_version = Column(String, default="prospectivity_v1")
    status = Column(String, default="queued")  # queued, running, completed, failed
    progress = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class ReportsORM(Base):
    """PDF export reports"""
    __tablename__ = "reports"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(PGUUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=True)
    report_type = Column(String)  # zone_prospectivity, basin_summary
    file_name = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, completed, failed
    file_size_mb = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class AuditLogORM(Base):
    """Change tracking"""
    __tablename__ = "audit_log"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_name = Column(String, nullable=False)
    action = Column(String, nullable=False)  # CREATE, UPDATE, DELETE
    changed_by = Column(String, default="system")
    changed_at = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON, default={})
