"""
API routes for job management — upload, status, results, list.
"""
import os
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Transaction, JobSummary, JobStatus
from app.schemas import (
    JobUploadResponse,
    JobResponse,
    JobStatusResponse,
    JobResultsResponse,
    JobSummaryResponse,
    TransactionResponse,
)
from app.services.csv_parser import validate_csv
from app.config import get_settings
from app.worker.tasks import process_job

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/upload", response_model=JobUploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Accept a CSV file upload, validate it, create a Job record,
    enqueue processing task, and return the job_id.
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted"
        )

    # Read file content
    try:
        content = await file.read()
        file_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File encoding error — please upload a UTF-8 encoded CSV"
        )

    # Validate CSV structure
    is_valid, error_msg = validate_csv(file_content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Save file to uploads directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(file_content)

    # Create Job record
    job = Job(
        filename=unique_filename,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue Celery task
    process_job.delay(str(job.id))

    logger.info(f"Job {job.id} created and enqueued for file: {file.filename}")

    return JobUploadResponse(
        job_id=job.id,
        status="pending",
        message=f"File '{file.filename}' uploaded successfully. Processing started.",
    )


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Return the current status of a job, with summary if completed."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    summary = None
    if job.status == JobStatus.COMPLETED and job.summary:
        summary = JobSummaryResponse(
            total_spend_inr=float(job.summary.total_spend_inr or 0),
            total_spend_usd=float(job.summary.total_spend_usd or 0),
            top_merchants=job.summary.top_merchants,
            anomaly_count=job.summary.anomaly_count or 0,
            narrative=job.summary.narrative,
            risk_level=job.summary.risk_level.value if job.summary.risk_level else None,
            category_breakdown=job.summary.category_breakdown,
        )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        filename=job.filename,
        row_count_raw=job.row_count_raw or 0,
        row_count_clean=job.row_count_clean or 0,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        summary=summary,
    )


@router.get("/{job_id}/results", response_model=JobResultsResponse)
async def get_job_results(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Return full structured results for a completed job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job.status.value}"
        )

    # Get all transactions
    transactions = db.query(Transaction).filter(Transaction.job_id == job.id).all()
    anomalies = [t for t in transactions if t.is_anomaly]

    # Build summary response
    summary = None
    if job.summary:
        summary = JobSummaryResponse(
            total_spend_inr=float(job.summary.total_spend_inr or 0),
            total_spend_usd=float(job.summary.total_spend_usd or 0),
            top_merchants=job.summary.top_merchants,
            anomaly_count=job.summary.anomaly_count or 0,
            narrative=job.summary.narrative,
            risk_level=job.summary.risk_level.value if job.summary.risk_level else None,
            category_breakdown=job.summary.category_breakdown,
        )

    return JobResultsResponse(
        job_id=job.id,
        status=job.status.value,
        filename=job.filename,
        summary=summary,
        transactions=[TransactionResponse.model_validate(t) for t in transactions],
        anomalies=[TransactionResponse.model_validate(t) for t in anomalies],
        total_transactions=len(transactions),
        total_anomalies=len(anomalies),
    )


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    db: Session = Depends(get_db),
):
    """List all jobs with optional status filtering."""
    query = db.query(Job)

    if status:
        try:
            status_enum = JobStatus(status.lower())
            query = query.filter(Job.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status filter: '{status}'. "
                       f"Valid values: pending, processing, completed, failed"
            )

    jobs = query.order_by(Job.created_at.desc()).all()
    return [JobResponse.model_validate(j) for j in jobs]
