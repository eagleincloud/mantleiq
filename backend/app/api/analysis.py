"""
Analysis job endpoints.
Trigger prospectivity analysis and check job status.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta
import logging
import uuid

from app.core.database import get_db
from app.models.schemas import RunAnalysisRequest, JobStatusResponse
from app.models.orm import AnalysisJobsORM, BasinORM

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/run", response_model=JobStatusResponse, status_code=202)
async def run_analysis(
    request: RunAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger prospectivity analysis for a basin.
    Returns immediately with job ID; analysis runs in background.

    Args:
        request: RunAnalysisRequest with basin_id, mode, model_version

    Returns:
        JobStatusResponse with job_id and initial status
    """
    try:
        # Verify basin exists
        basin = db.query(BasinORM).filter(BasinORM.id == request.basin_id).first()
        if not basin:
            raise HTTPException(status_code=404, detail="Basin not found")

        # Create analysis job record
        job_id = str(uuid.uuid4())
        job = AnalysisJobsORM(
            id=job_id,
            basin_id=request.basin_id,
            mode=request.mode,
            model_version=request.model_version,
            status="queued",
            progress=0,
            started_at=None,
            completed_at=None,
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        # Queue background task (Phase 2: actual implementation)
        # background_tasks.add_task(compute_analysis, job_id, request.basin_id)

        logger.info(f"Analysis job {job_id} queued for basin {request.basin_id}")

        return JobStatusResponse(
            analysis_id=job_id,
            status="queued",
            basin_id=request.basin_id,
            mode=request.mode,
            progress=0,
            started_at=None,
            completed_at=None,
            error_message=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating analysis job: {e}")
        raise HTTPException(status_code=500, detail="Failed to create analysis job")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Check status of an analysis job.

    Args:
        job_id: Analysis job UUID

    Returns:
        Current job status with progress and timestamps
    """
    try:
        # Query job
        job = db.query(AnalysisJobsORM).filter(AnalysisJobsORM.id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return JobStatusResponse(
            analysis_id=str(job.id),
            status=job.status,
            basin_id=str(job.basin_id),
            mode=job.mode,
            progress=job.progress,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job status")


@router.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str, db: Session = Depends(get_db)):
    """
    Get analysis results for a completed job.

    Args:
        job_id: Analysis job UUID

    Returns:
        Analysis results if job is completed, error if still running/failed
    """
    try:
        # Query job
        job = db.query(AnalysisJobsORM).filter(AnalysisJobsORM.id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Check status
        if job.status == "queued" or job.status == "running":
            raise HTTPException(
                status_code=202,
                detail=f"Job still {job.status} (progress: {job.progress}%)",
            )

        if job.status == "failed":
            raise HTTPException(status_code=400, detail=f"Job failed: {job.error_message}")

        # Job is completed, return results
        # (Phase 2: fetch from results table)
        return {
            "job_id": job_id,
            "basin_id": str(job.basin_id),
            "status": job.status,
            "completed_at": job.completed_at,
            "results_available": True,
            # Future: zones, scores, rankings, etc.
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job results {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve results")
