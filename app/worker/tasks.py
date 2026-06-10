"""
Celery task — orchestrates the full transaction processing pipeline.

Pipeline steps:
1. Parse CSV file
2. Clean & normalize data
3. Store cleaned transactions in DB
4. Detect anomalies
5. Classify uncategorized transactions (LLM)
6. Generate narrative summary (LLM)
7. Mark job as completed
"""
import logging
import traceback
from datetime import datetime
from decimal import Decimal

from app.worker.celery_app import celery_app
from app.database import SessionLocal
from app.models import Job, Transaction, JobSummary, JobStatus, RiskLevel
from app.services.csv_parser import parse_csv
from app.services.data_cleaner import clean_rows
from app.services.anomaly_detector import detect_anomalies
from app.services.llm_classifier import classify_transactions
from app.services.llm_summarizer import generate_summary

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_job")
def process_job(self, job_id: str):
    """
    Main pipeline task. Processes a CSV upload through all stages.
    """
    db = SessionLocal()

    try:
        # --- Fetch job ---
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return {"status": "error", "message": "Job not found"}

        # --- Update status to processing ---
        job.status = JobStatus.PROCESSING
        db.commit()
        logger.info(f"[Job {job_id}] Starting processing pipeline")

        # --- Step 1: Read CSV file ---
        file_path = f"uploads/{job.filename}"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()
        except FileNotFoundError:
            raise Exception(f"Upload file not found: {file_path}")

        # --- Step 2: Parse CSV ---
        raw_rows = parse_csv(file_content)
        job.row_count_raw = len(raw_rows)
        db.commit()
        logger.info(f"[Job {job_id}] Parsed {len(raw_rows)} raw rows")

        # --- Step 3: Clean data ---
        cleaned_rows = clean_rows(raw_rows)
        job.row_count_clean = len(cleaned_rows)
        db.commit()
        logger.info(f"[Job {job_id}] Cleaned to {len(cleaned_rows)} rows")

        # --- Step 4: Detect anomalies ---
        cleaned_rows = detect_anomalies(cleaned_rows)
        logger.info(f"[Job {job_id}] Anomaly detection complete")

        # --- Step 5: LLM classification ---
        cleaned_rows = classify_transactions(cleaned_rows)
        logger.info(f"[Job {job_id}] LLM classification complete")

        # --- Step 6: Store transactions in DB ---
        for row in cleaned_rows:
            txn = Transaction(
                job_id=job.id,
                txn_id=row.get("txn_id"),
                date=row.get("date"),
                merchant=row.get("merchant"),
                amount=Decimal(str(row["amount"])) if row.get("amount") is not None else None,
                currency=row.get("currency"),
                status=row.get("status"),
                category=row.get("category"),
                account_id=row.get("account_id"),
                is_anomaly=row.get("is_anomaly", False),
                anomaly_reason=row.get("anomaly_reason"),
                llm_category=row.get("llm_category"),
                llm_raw_response=row.get("llm_raw_response"),
                llm_failed=row.get("llm_failed", False),
                notes=row.get("notes"),
            )
            db.add(txn)
        db.commit()
        logger.info(f"[Job {job_id}] Stored {len(cleaned_rows)} transactions in DB")

        # --- Step 7: Generate summary ---
        summary_data = generate_summary(cleaned_rows)

        # Map risk_level string to enum
        risk_level_map = {"low": RiskLevel.LOW, "medium": RiskLevel.MEDIUM, "high": RiskLevel.HIGH}
        risk_enum = risk_level_map.get(summary_data.get("risk_level", "low"), RiskLevel.LOW)

        job_summary = JobSummary(
            job_id=job.id,
            total_spend_inr=Decimal(str(summary_data["total_spend_inr"])),
            total_spend_usd=Decimal(str(summary_data["total_spend_usd"])),
            top_merchants=summary_data["top_merchants"],
            anomaly_count=summary_data["anomaly_count"],
            narrative=summary_data["narrative"],
            risk_level=risk_enum,
            category_breakdown=summary_data["category_breakdown"],
        )
        db.add(job_summary)
        logger.info(f"[Job {job_id}] Summary generated")

        # --- Step 8: Mark completed ---
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"[Job {job_id}] ✅ Pipeline complete!")
        return {
            "status": "completed",
            "job_id": job_id,
            "rows_processed": len(cleaned_rows),
            "anomalies_found": summary_data["anomaly_count"],
        }

    except Exception as e:
        logger.error(f"[Job {job_id}] Pipeline failed: {e}\n{traceback.format_exc()}")
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)[:1000]
                db.commit()
        except Exception:
            pass
        raise

    finally:
        db.close()
