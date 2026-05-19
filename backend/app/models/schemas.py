"""Pydantic schemas for API requests and responses"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# BASIN SCHEMAS
# ============================================================================

class BasinBase(BaseModel):
    """Base basin schema"""
    name: str = Field(..., description="Basin name")
    region: Optional[str] = Field(None, description="Geographic region")
    country: Optional[str] = Field(None, description="Country")
    description: Optional[str] = Field(None, description="Basin description")


class BasinCreate(BasinBase):
    """Schema for creating a basin"""
    pass


class BasinResponse(BasinBase):
    """Schema for basin API response"""
    id: str = Field(..., description="Basin UUID")
    data_coverage_score: Optional[float] = Field(None, description="Data coverage (0-1)")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# ANALYSIS JOB SCHEMAS
# ============================================================================

class RunAnalysisRequest(BaseModel):
    """Request to run prospectivity analysis"""
    basin_id: str = Field(..., description="Basin UUID to analyze")
    mode: str = Field("standard", description="Analysis mode: standard, fast, comprehensive")
    model_version: str = Field("prospectivity_v1", description="Model version to use")
    force_recompute: bool = Field(False, description="Force full recomputation (skip cache)")


class JobStatusResponse(BaseModel):
    """Response for job status query"""
    analysis_id: str = Field(..., description="Analysis job UUID")
    status: str = Field(..., description="Job status: queued, running, completed, failed")
    basin_id: str = Field(..., description="Basin UUID")
    mode: str = Field(..., description="Analysis mode")
    progress: int = Field(0, description="Progress percentage (0-100)")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")


# ============================================================================
# FEATURE SCHEMAS
# ============================================================================

class FeatureContribution(BaseModel):
    """Single feature contribution to score"""
    name: str = Field(..., description="Feature name")
    label: str = Field(..., description="Human-readable feature label")
    value: float = Field(..., description="Feature value (0-1)")
    weight: float = Field(..., description="Feature weight in scoring")
    contribution: float = Field(..., description="Contribution to score (%)")


# ============================================================================
# ZONE SCHEMAS
# ============================================================================

class ZoneScoreComponents(BaseModel):
    """Score component breakdown"""
    f_generation: float = Field(..., description="Hydrogen generation score")
    f_fluid_interaction: float = Field(..., description="Fluid interaction score")
    f_structural_pathways: float = Field(..., description="Structural pathways score")
    f_trap_retention: float = Field(..., description="Trap retention score")
    f_surface_indicators: float = Field(..., description="Surface indicators score")
    f_thermodynamic: float = Field(..., description="Thermodynamic score")


class ZoneBasicInfo(BaseModel):
    """Basic zone information (for listing)"""
    id: str = Field(..., description="Zone UUID")
    name: str = Field(..., description="Zone name")
    rank: int = Field(..., description="Ranking within basin")
    prospectivity_score: float = Field(..., description="Final prospectivity score (0-100)")
    confidence_score: float = Field(..., description="Confidence modifier (0.5-1.0)")
    centroid: List[float] = Field(..., description="Zone center [lon, lat]")


class ZoneDetailResponse(BaseModel):
    """Detailed zone information"""
    id: str = Field(..., description="Zone UUID")
    name: str = Field(..., description="Zone name")
    rank: int = Field(..., description="Ranking")
    centroid: List[float] = Field(..., description="Center [lon, lat]")
    prospectivity_score: float = Field(..., description="Score (0-100)")
    confidence_score: float = Field(..., description="Confidence (0.5-1.0)")
    score_class: str = Field(..., description="Score interpretation")

    # Score Components
    components: ZoneScoreComponents = Field(..., description="Component scores")

    # Attribution
    top_features: List[FeatureContribution] = Field(..., description="Top 4 contributing features")
    missing_data_caveats: List[str] = Field(default_factory=list, description="Data quality warnings")
    explanation_summary: str = Field(..., description="Natural language explanation")
    recommended_next_actions: List[str] = Field(default_factory=list, description="Next step recommendations")


class AnalysisResultsResponse(BaseModel):
    """Analysis results for a basin"""
    basin_id: str = Field(..., description="Basin UUID")
    basin_name: str = Field(..., description="Basin name")
    basin_score: float = Field(..., description="Basin-level average score")
    confidence: float = Field(..., description="Basin-level average confidence")
    zone_count: int = Field(..., description="Number of prospect zones")
    zones: List[ZoneBasicInfo] = Field(default_factory=list, description="Top zones")


# ============================================================================
# COMPARISON SCHEMAS
# ============================================================================

class CompareZonesRequest(BaseModel):
    """Request to compare multiple zones"""
    zone_ids: List[str] = Field(..., description="List of zone UUIDs to compare", min_items=2, max_items=10)


class ComparisonResult(BaseModel):
    """Comparison result for multiple zones"""
    zones: List[ZoneDetailResponse] = Field(..., description="Zone details")
    summary: str = Field(..., description="Text summary of comparison")


# ============================================================================
# EXPORT SCHEMAS
# ============================================================================

class ExportReportRequest(BaseModel):
    """Request to export zone as PDF"""
    zone_id: str = Field(..., description="Zone UUID to export")
    include_map: bool = Field(True, description="Include zone map in PDF")
    include_recommendations: bool = Field(True, description="Include next actions")


class ExportReportResponse(BaseModel):
    """Response for report export"""
    status: str = Field(..., description="Export status: created, pending, failed")
    file_path: str = Field(..., description="S3/GCS URI to PDF")
    file_size_mb: Optional[float] = Field(None, description="File size in MB")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    download_url: Optional[str] = Field(None, description="Temporary download URL")


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Error class name")
    error_code: Optional[str] = Field(None, description="Internal error code")

