import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime,
    ForeignKey, Enum, Numeric, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    row_count_raw = Column(Integer, default=0)
    row_count_clean = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    transactions = relationship(
        "Transaction", back_populates="job", cascade="all, delete-orphan"
    )
    summary = relationship(
        "JobSummary", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Job {self.id} status={self.status}>"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True)
    txn_id = Column(String(50), nullable=True)
    date = Column(DateTime, nullable=True)
    merchant = Column(String(255), nullable=True)
    amount = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=True)
    status = Column(String(20), nullable=True)
    category = Column(String(100), nullable=True)
    account_id = Column(String(50), nullable=True, index=True)
    is_anomaly = Column(Boolean, default=False)
    anomaly_reason = Column(Text, nullable=True)
    llm_category = Column(String(100), nullable=True)
    llm_raw_response = Column(Text, nullable=True)
    llm_failed = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    job = relationship("Job", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction {self.txn_id} amount={self.amount} {self.currency}>"


class JobSummary(Base):
    __tablename__ = "job_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), unique=True, nullable=False
    )
    total_spend_inr = Column(Numeric(14, 2), default=0)
    total_spend_usd = Column(Numeric(14, 2), default=0)
    top_merchants = Column(JSON, nullable=True)
    anomaly_count = Column(Integer, default=0)
    narrative = Column(Text, nullable=True)
    risk_level = Column(Enum(RiskLevel), nullable=True)
    category_breakdown = Column(JSON, nullable=True)

    job = relationship("Job", back_populates="summary")

    def __repr__(self):
        return f"<JobSummary job={self.job_id} risk={self.risk_level}>"
