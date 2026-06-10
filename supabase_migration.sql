-- ═══════════════════════════════════════════════════════════════════════════
-- AI Transaction Pipeline — Supabase Database Schema Migration
-- ═══════════════════════════════════════════════════════════════════════════
-- 
-- This SQL script creates all necessary tables for the transaction pipeline.
-- Compatible with Supabase (PostgreSQL 16+)
-- 
-- Tables created:
-- 1. jobs - Main job records
-- 2. transactions - Individual transaction records
-- 3. job_summaries - Processing summaries
--
-- Run this in Supabase SQL Editor to set up the database.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════════════
-- Table: jobs
-- Purpose: Store metadata about each CSV upload and processing job
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  filename VARCHAR(255) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- Valid values: pending, processing, completed, failed
  row_count_raw INTEGER DEFAULT 0,
  row_count_clean INTEGER DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMP,
  error_message TEXT,
  
  -- Constraints and indexes
  CONSTRAINT status_check CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);

-- ═══════════════════════════════════════════════════════════════════════════
-- Table: transactions
-- Purpose: Store cleaned and processed transaction records
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS transactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  
  -- Raw transaction fields
  txn_id VARCHAR(50),
  date TIMESTAMP,
  merchant VARCHAR(255),
  amount NUMERIC(12, 2),
  currency VARCHAR(3) DEFAULT 'INR',
  status VARCHAR(20),
  category VARCHAR(100),
  account_id VARCHAR(50),
  notes TEXT,
  
  -- Anomaly detection fields
  is_anomaly BOOLEAN DEFAULT FALSE,
  anomaly_reason TEXT,
  
  -- LLM classification fields
  llm_category VARCHAR(100),
  llm_raw_response TEXT,
  llm_failed BOOLEAN DEFAULT FALSE,
  
  -- Indexes
  CONSTRAINT job_fk FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_transactions_job_id ON transactions(job_id);
CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_is_anomaly ON transactions(is_anomaly);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date DESC);

-- ═══════════════════════════════════════════════════════════════════════════
-- Table: job_summaries
-- Purpose: Store aggregated analysis and narrative for each job
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS job_summaries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id UUID NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
  
  -- Financial metrics
  total_spend_inr NUMERIC(14, 2) DEFAULT 0,
  total_spend_usd NUMERIC(14, 2) DEFAULT 0,
  
  -- Analysis results
  top_merchants JSONB,
  anomaly_count INTEGER DEFAULT 0,
  category_breakdown JSONB,
  
  -- Narrative and risk
  narrative TEXT,
  risk_level VARCHAR(20),
    -- Valid values: low, medium, high
  
  -- Constraint
  CONSTRAINT risk_level_check CHECK (risk_level IN ('low', 'medium', 'high', NULL))
);

CREATE INDEX IF NOT EXISTS idx_job_summaries_job_id ON job_summaries(job_id);
CREATE INDEX IF NOT EXISTS idx_job_summaries_risk_level ON job_summaries(risk_level);

-- ═══════════════════════════════════════════════════════════════════════════
-- Optional: Row-Level Security (RLS) for multi-tenancy
-- Uncomment if you want to implement RLS
-- ═══════════════════════════════════════════════════════════════════════════

-- ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE job_summaries ENABLE ROW LEVEL SECURITY;

-- ═══════════════════════════════════════════════════════════════════════════
-- Sample Data (Optional) — for testing purposes
-- Uncomment the INSERT statements below to populate sample data
-- ═══════════════════════════════════════════════════════════════════════════

-- INSERT INTO jobs (filename, status, row_count_raw, row_count_clean)
-- VALUES ('sample_transactions.csv', 'completed', 100, 98);

-- ═══════════════════════════════════════════════════════════════════════════
-- End of Migration
-- ═══════════════════════════════════════════════════════════════════════════
