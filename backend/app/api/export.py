"""
Export and reporting endpoints.
Generate PDF reports and export analysis results.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import uuid
import os

from app.core.database import get_db
from app.models.schemas import ExportReportRequest, ExportReportResponse
from app.models.orm import ReportsORM, ZonesORM, ModelOutputsORM, BasinORM
from app.services.export import PDFReportGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])

# Temporary storage for reports (Phase 2: use GCS)
REPORTS_DIR = "/tmp/mantleiq_reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


@router.post("/report", response_model=ExportReportResponse, status_code=202)
async def export_report(
    request: ExportReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Generate a PDF report for a zone (async, returns immediately).

    Args:
        request: ExportReportRequest with zone_id and options

    Returns:
        ExportReportResponse with status and file path
    """
    try:
        # Verify zone exists
        zone = db.query(ZonesORM).filter(ZonesORM.id == request.zone_id).first()
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")

        # Create report record
        report_id = str(uuid.uuid4())
        file_name = f"zone_{request.zone_id[:8]}_{report_id}.pdf"
        file_path = f"/tmp/mantleiq_reports/{file_name}"

        report = ReportsORM(
            id=report_id,
            zone_id=request.zone_id,
            report_type="zone_prospectivity",
            file_name=file_name,
            file_path=file_path,
            status="pending",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        # Queue background task
        background_tasks.add_task(generate_pdf_report, report_id, request.zone_id, file_path)

        logger.info(f"Report {report_id} queued for zone {request.zone_id}")

        return ExportReportResponse(
            status="pending",
            file_path=file_path,
            file_size_mb=None,
            expires_at=report.expires_at,
            download_url=f"/export/reports/{report_id}/download",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating export report: {e}")
        raise HTTPException(status_code=500, detail="Failed to create report")


@router.get("/reports/{report_id}")
async def get_report_status(report_id: str, db: Session = Depends(get_db)):
    """
    Check status of a report generation job.

    Args:
        report_id: Report UUID

    Returns:
        Report status and metadata
    """
    try:
        report = db.query(ReportsORM).filter(ReportsORM.id == report_id).first()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        # Check if expired
        if report.expires_at and datetime.utcnow() > report.expires_at:
            return {
                "status": "expired",
                "report_id": report_id,
                "message": "Report has expired and is no longer available",
            }

        return {
            "status": report.status,
            "report_id": report_id,
            "zone_id": str(report.zone_id),
            "file_name": report.file_name,
            "created_at": report.created_at,
            "expires_at": report.expires_at,
            "file_size_mb": report.file_size_mb,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving report {report_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve report")


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str, db: Session = Depends(get_db)):
    """
    Download a generated report PDF.

    Args:
        report_id: Report UUID

    Returns:
        PDF file download
    """
    try:
        report = db.query(ReportsORM).filter(ReportsORM.id == report_id).first()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        # Check status
        if report.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Report status is {report.status}, not ready for download",
            )

        # Check if expired
        if report.expires_at and datetime.utcnow() > report.expires_at:
            raise HTTPException(status_code=410, detail="Report has expired")

        # Check if file exists
        if not os.path.exists(report.file_path):
            logger.error(f"Report file not found: {report.file_path}")
            raise HTTPException(status_code=404, detail="Report file not found")

        # Return file
        return FileResponse(
            path=report.file_path,
            filename=report.file_name,
            media_type="application/pdf",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report {report_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download report")


@router.get("/basins/{basin_id}/results")
async def export_basin_results(basin_id: str, format: str = "geojson", db: Session = Depends(get_db)):
    """
    Export all results for a basin in various formats.

    Args:
        basin_id: Basin UUID
        format: Export format (geojson, csv, json)

    Returns:
        Exported data in requested format
    """
    try:
        # Query zones for basin
        zones = db.query(ZonesORM).filter(ZonesORM.basin_id == basin_id).all()

        if not zones:
            raise HTTPException(status_code=404, detail="No results found for basin")

        if format == "geojson":
            return _export_geojson(zones, db)
        elif format == "csv":
            return _export_csv(zones, db)
        elif format == "json":
            return _export_json(zones, db)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting basin {basin_id} results: {e}")
        raise HTTPException(status_code=500, detail="Failed to export results")


def _export_geojson(zones, db):
    """Export zones as GeoJSON FeatureCollection."""
    features = []
    for zone in zones:
        # Query model output for scores
        model_output = db.query(ModelOutputsORM).filter(
            ModelOutputsORM.zone_id == zone.id
        ).first()

        feature = {
            "type": "Feature",
            "properties": {
                "zone_id": str(zone.id),
                "name": zone.name,
                "score": model_output.final_score * 100 if model_output else 0,
                "confidence": model_output.confidence_score if model_output else 0.5,
                "rank": model_output.rank if model_output else 0,
            },
            "geometry": None,  # Phase 2: extract from zone.geometry
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def _export_csv(zones, db):
    """Export zones as CSV."""
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["zone_id", "name", "score", "confidence", "rank"],
    )
    writer.writeheader()

    for zone in zones:
        model_output = db.query(ModelOutputsORM).filter(
            ModelOutputsORM.zone_id == zone.id
        ).first()

        writer.writerow({
            "zone_id": str(zone.id),
            "name": zone.name,
            "score": model_output.final_score * 100 if model_output else 0,
            "confidence": model_output.confidence_score if model_output else 0.5,
            "rank": model_output.rank if model_output else 0,
        })

    return output.getvalue()


def _export_json(zones, db):
    """Export zones as JSON."""
    zones_data = []
    for zone in zones:
        model_output = db.query(ModelOutputsORM).filter(
            ModelOutputsORM.zone_id == zone.id
        ).first()

        zones_data.append({
            "zone_id": str(zone.id),
            "name": zone.name,
            "score": model_output.final_score * 100 if model_output else 0,
            "confidence": model_output.confidence_score if model_output else 0.5,
            "rank": model_output.rank if model_output else 0,
        })

    return {"zones": zones_data}


def generate_pdf_report(report_id: str, zone_id: str, file_path: str):
    """
    Generate PDF report for a zone (background task).

    Args:
        report_id: Report UUID
        zone_id: Zone UUID
        file_path: Path to save PDF file
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        # Fetch zone
        zone = db.query(ZonesORM).filter(ZonesORM.id == zone_id).first()
        if not zone:
            logger.error(f"Zone {zone_id} not found for report {report_id}")
            _update_report_status(report_id, "failed", db, error="Zone not found")
            return

        # Fetch basin
        basin = db.query(BasinORM).filter(BasinORM.id == zone.basin_id).first()
        if not basin:
            logger.error(f"Basin {zone.basin_id} not found for report {report_id}")
            _update_report_status(report_id, "failed", db, error="Basin not found")
            return

        # Fetch model output for scores and attribution
        model_output = db.query(ModelOutputsORM).filter(
            ModelOutputsORM.zone_id == zone_id
        ).first()

        if not model_output:
            logger.error(f"Model output not found for zone {zone_id}")
            _update_report_status(report_id, "failed", db, error="Model output not found")
            return

        # Prepare data for PDF generation
        final_score = model_output.final_score if model_output.final_score else 0.5
        final_rank = model_output.rank if model_output.rank else 50

        # Get score interpretation
        score_percentile = final_score * 100
        if score_percentile >= 80:
            score_class = "High-priority target"
        elif score_percentile >= 65:
            score_class = "Strong prospect, needs validation"
        elif score_percentile >= 50:
            score_class = "Moderate prospect"
        elif score_percentile >= 35:
            score_class = "Weak / speculative"
        else:
            score_class = "Low priority"

        # Extract components
        score_components = model_output.components if model_output.components else {}
        if not score_components:
            # Provide defaults if not available
            score_components = {
                "f_generation": 0.5,
                "f_fluid_interaction": 0.5,
                "f_structural_pathways": 0.5,
                "f_trap_retention": 0.5,
                "f_surface_indicators": 0.5,
                "f_thermodynamic": 0.5,
            }

        # Extract top features
        top_features = model_output.top_features if model_output.top_features else []
        if not isinstance(top_features, list):
            top_features = []

        # Extract or generate narrative and recommendations
        narrative_summary = model_output.explanation_summary or f"Zone scored {score_percentile:.1f}th percentile ({score_class})."

        # Generate recommendations based on score
        recommended_actions = []
        if score_percentile >= 80:
            recommended_actions.append("Prioritize for drilling prospects")
            recommended_actions.append("Acquire high-resolution seismic data")
        elif score_percentile >= 65:
            recommended_actions.append("Conduct detailed geological mapping")
            recommended_actions.append("Perform pressure-temperature modeling")
        elif score_percentile >= 50:
            recommended_actions.append("Assess economic viability")
            recommended_actions.append("Study analog basin analogs")
        else:
            recommended_actions.append("Monitor for additional data")
            recommended_actions.append("Consider for future re-evaluation")

        # Generate missing data caveats
        missing_data_caveats = []
        confidence = model_output.confidence_score if model_output.confidence_score else 0.8
        if confidence < 0.6:
            missing_data_caveats.append("Low confidence due to incomplete or poor-quality data")
        elif confidence < 0.7:
            missing_data_caveats.append("Moderate confidence - recommend field verification")

        # Generate PDF
        generator = PDFReportGenerator()
        pdf_bytes = generator.generate_report(
            zone_name=zone.name or f"Zone {zone_id[:8]}",
            basin_name=basin.name or "Unknown Basin",
            final_score=final_score,
            final_rank=final_rank,
            score_class=score_class,
            score_components=score_components,
            top_features=top_features,
            missing_data_caveats=missing_data_caveats,
            narrative_summary=narrative_summary,
            recommended_actions=recommended_actions,
            confidence_score=confidence,
        )

        # Save PDF to file
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        file_size_mb = len(pdf_bytes) / (1024 * 1024)
        _update_report_status(report_id, "completed", db, file_size_mb=file_size_mb)
        logger.info(f"Report {report_id} generated successfully ({file_size_mb:.2f} MB)")

    except Exception as e:
        logger.error(f"Error generating PDF report {report_id}: {e}", exc_info=True)
        _update_report_status(report_id, "failed", db, error=str(e))
    finally:
        db.close()


def _update_report_status(report_id: str, status: str, db: Session, file_size_mb: float = None, error: str = None):
    """Update report status in database."""
    try:
        report = db.query(ReportsORM).filter(ReportsORM.id == report_id).first()
        if report:
            report.status = status
            if file_size_mb:
                report.file_size_mb = file_size_mb
            db.commit()
    except Exception as e:
        logger.error(f"Error updating report {report_id} status: {e}")
