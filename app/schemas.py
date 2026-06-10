from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class JobStatusEnum(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class RiskLevelEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# ─── Job Schemas ─────────────────────────────────────────────

class JobUploadResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


class JobResponse(BaseModel):
    id: UUID
    filename: str
    status: JobStatusEnum
    row_count_raw: int
    row_count_clean: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Transaction Schemas ─────────────────────────────────────

class TransactionResponse(BaseModel):
    id: UUID
    txn_id: Optional[str] = None
    date: Optional[datetime] = None
    merchant: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    account_id: Optional[str] = None
    is_anomaly: bool = False
    anomaly_reason: Optional[str] = None
    llm_category: Optional[str] = None
    llm_failed: bool = False
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Summary Schemas ─────────────────────────────────────────

class JobSummaryResponse(BaseModel):
    total_spend_inr: float = 0
    total_spend_usd: float = 0
    top_merchants: Optional[Any] = None
    anomaly_count: int = 0
    narrative: Optional[str] = None
    risk_level: Optional[str] = None
    category_breakdown: Optional[Any] = None

    class Config:
        from_attributes = True


# ─── Composite Response Schemas ──────────────────────────────

class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatusEnum
    filename: str
    row_count_raw: int
    row_count_clean: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    summary: Optional[JobSummaryResponse] = None


class JobResultsResponse(BaseModel):
    job_id: UUID
    status: JobStatusEnum
    filename: str
    summary: Optional[JobSummaryResponse] = None
    transactions: List[TransactionResponse] = []
    anomalies: List[TransactionResponse] = []
    total_transactions: int = 0
    total_anomalies: int = 0
    total_transactions: int = 0
    total_anomalies: int = 0
