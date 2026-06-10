# End-to-End Flow Documentation

This document explains the complete transaction processing pipeline and how to verify it works correctly.

---

## 1. System Architecture

```
User → Frontend UI
  ↓
[Upload CSV] 
  ↓
FastAPI (/api/jobs/upload)
  ├─ Validates CSV structure
  ├─ Saves file to disk
  ├─ Creates Job record (PENDING)
  └─ Enqueues Celery task
  ↓
Redis (Job Broker)
  ↓
Celery Worker
  ├─ Step 1: Parse CSV → Raw rows
  ├─ Step 2: Clean data → Normalized rows
  ├─ Step 3: Detect anomalies → Flagged rows
  ├─ Step 4: Classify transactions (LLM/Rules)
  ├─ Step 5: Store in PostgreSQL
  ├─ Step 6: Generate summary (LLM/Rules)
  ├─ Step 7: Update Job status → COMPLETED
  └─ Store summary in DB
  ↓
User checks status (/api/jobs/{job_id}/status)
  ├─ Status: PENDING → "Still processing"
  ├─ Status: PROCESSING → "In progress"
  ├─ Status: COMPLETED → Returns summary
  └─ Status: FAILED → Returns error message
  ↓
User retrieves results (/api/jobs/{job_id}/results)
  ├─ All transactions
  ├─ Flagged anomalies
  ├─ Financial summary
  ├─ Risk assessment
  └─ Spending narrative
```

---

## 2. Processing Pipeline Details

### Stage 1: CSV Parsing
**Purpose**: Validate and read uploaded CSV

**Input**: Raw CSV file
```
txn_id,date,merchant,amount,currency,status,category,account_id,notes
TXN001,04-09-2024,Flipkart,10882.55,INR,SUCCESS,Shopping,ACC003,Refund expected
```

**Output**: Dictionary of rows
```python
{
  "txn_id": "TXN001",
  "date": "04-09-2024",
  "merchant": "Flipkart",
  "amount": "10882.55",
  "currency": "INR",
  "status": "SUCCESS",
  "category": "Shopping",
  "account_id": "ACC003",
  "notes": "Refund expected"
}
```

### Stage 2: Data Cleaning
**Purpose**: Normalize and deduplicate data

**Transformations**:
- 📅 **Date normalization**: Multiple formats → ISO datetime
  - `04-09-2024` (DD-MM-YYYY)
  - `2024/02/05` (YYYY/MM/DD)
  - `2024-02-05` (ISO)
  
- 💰 **Amount parsing**: Strip currency symbols
  - `$450.00` → `450.00`
  - `₹10882.55` → `10882.55`
  
- 🔤 **Status normalization**: Uppercase
  - `success` → `SUCCESS`
  - `failed` → `FAILED`
  
- 💳 **Currency normalization**: Uppercase
  - `inr` → `INR`
  - `usd` → `USD`
  
- 🏷️ **Category**: Default to "Uncategorised" if missing
  
- 🆔 **Transaction ID**: Generate if missing
  - Format: `GEN-XXXXXXXX` (random hex)
  
- ⚠️ **Deduplication**: Remove exact duplicates

**Output**: Cleaned transaction list
```python
{
  "txn_id": "TXN001",
  "date": datetime(2024, 9, 4),
  "merchant": "Flipkart",
  "amount": Decimal("10882.55"),
  "currency": "INR",
  "status": "SUCCESS",
  "category": "Shopping",
  "account_id": "ACC003",
  "notes": "Refund expected"
}
```

### Stage 3: Anomaly Detection
**Purpose**: Flag suspicious transactions

**Detection Rules**:

1. **Statistical Outlier** (Amount > 3× account median)
   - Example: If ACC003 median = $5000, and transaction = $20000
   - Flag: "Amount ($20000) exceeds 3x account median ($5000)"

2. **Currency Mismatch** (USD + domestic-only merchant)
   - Example: Zomato (domestic) with USD currency
   - Flag: "Currency mismatch: Zomato is domestic-only but currency is USD"

3. **Suspicious Keywords** in notes
   - "SUSPICIOUS" → Flag: "Flagged as SUSPICIOUS in notes"
   - "Duplicate?" → Flag: "Flagged as potential Duplicate in notes"

**Output**: Transactions with `is_anomaly` flag and `anomaly_reason`
```python
{
  "is_anomaly": True,
  "anomaly_reason": "Amount ($14670.87) exceeds 3x account median ($5000.00)"
}
```

### Stage 4: LLM Classification
**Purpose**: Categorize uncategorized transactions

**Two Modes**:

**Mode A: LLM-based** (if GEMINI_API_KEY available)
- Uses Google Gemini 1.5 Flash
- Batch size: 10 transactions per API call
- Categories: Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, Other
- Retries: 3 attempts with exponential backoff
- Cost: ~$0.001 per batch

**Example Prompt**:
```
Classify each transaction into: Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, Other

Transactions:
1. merchant="Swiggy", amount=10634.88, notes=""
2. merchant="HDFC ATM", amount=1117.58, notes=""

Respond with: [{"index": 1, "category": "Food"}, {"index": 2, "category": "Cash Withdrawal"}]
```

**Mode B: Rule-based** (fallback, no API key needed)
- Uses merchant-to-category mapping
- Instant, free, deterministic
- Fallback when LLM unavailable or fails

**Merchant Mappings**:
```python
{
  "swiggy": "Food",
  "zomato": "Food",
  "flipkart": "Shopping",
  "amazon": "Shopping",
  "uber": "Transport",
  "irctc": "Travel",
  "netflix": "Entertainment",
  # ... etc
}
```

### Stage 5: Database Storage
**Purpose**: Persist all processed data

**Tables Populated**:
1. `jobs` - Updated with final row counts
2. `transactions` - Insert all cleaned rows
3. `job_summaries` - Financial analysis

### Stage 6: Summary Generation
**Purpose**: Create spending analysis

**Computed Metrics**:
- Total spend by currency (INR, USD)
- Top 3 merchants by spending
- Anomaly count
- Category breakdown
- Risk level calculation:
  - `HIGH`: >20% anomaly ratio
  - `MEDIUM`: 10-20% anomaly ratio
  - `LOW`: <10% anomaly ratio

**Two Modes**:

**Mode A: LLM Narrative** (if GEMINI_API_KEY available)
- Generates 2-3 sentence spending analysis
- Analyzes spending patterns and trends
- Risk assessment with context

Example output:
```
"Analysis of 20 transactions reveals total spending of ₹145,287.42 INR 
and $2,978.06 USD. Top merchants by spend are Amazon, Flipkart, and Swiggy. 
3 transactions were flagged as anomalous, resulting in a medium risk assessment."
```

**Mode B: Fallback Narrative** (no API key)
- Template-based, deterministic
- Still provides key insights

### Stage 7: Job Completion
**Purpose**: Mark job as COMPLETED and return summary

**Final Job Status**:
```python
{
  "job_id": "uuid",
  "status": "COMPLETED",
  "filename": "transactions.csv",
  "row_count_raw": 100,
  "row_count_clean": 98,  # 2 duplicates removed
  "created_at": "2024-12-20T10:30:00Z",
  "completed_at": "2024-12-20T10:35:15Z",
  "summary": {
    "total_spend_inr": 145287.42,
    "total_spend_usd": 2978.06,
    "anomaly_count": 3,
    "risk_level": "medium",
    "category_breakdown": {
      "Food": 25000,
      "Shopping": 85000,
      "Transport": 15000,
      "Other": 20287.42
    },
    "narrative": "...",
    "top_merchants": [
      {"name": "Amazon", "total": 50000},
      {"name": "Flipkart", "total": 35000},
      {"name": "Swiggy", "total": 20000}
    ]
  }
}
```

---

## 3. API Endpoints

### POST /api/jobs/upload
**Upload a CSV file for processing**

Request:
```bash
curl -X POST http://localhost:8000/api/jobs/upload \
  -F "file=@transactions.csv"
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "File 'transactions.csv' uploaded successfully. Processing started."
}
```

### GET /api/jobs/{job_id}/status
**Check current processing status**

Request:
```bash
curl http://localhost:8000/api/jobs/{job_id}/status
```

Response (processing):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "filename": "transactions.csv",
  "row_count_raw": 0,
  "row_count_clean": 0,
  "created_at": "2024-12-20T10:30:00Z",
  "summary": null
}
```

Response (completed):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "filename": "transactions.csv",
  "row_count_raw": 100,
  "row_count_clean": 98,
  "created_at": "2024-12-20T10:30:00Z",
  "completed_at": "2024-12-20T10:35:15Z",
  "summary": { /* summary data */ }
}
```

### GET /api/jobs/{job_id}/results
**Get full results (only when completed)**

Request:
```bash
curl http://localhost:8000/api/jobs/{job_id}/results
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "filename": "transactions.csv",
  "summary": { /* summary */ },
  "transactions": [ /* all transactions */ ],
  "anomalies": [ /* flagged transactions */ ],
  "total_transactions": 98,
  "total_anomalies": 3
}
```

### GET /api/jobs
**List all jobs with optional filtering**

Request:
```bash
curl http://localhost:8000/api/jobs
curl http://localhost:8000/api/jobs?status=completed
curl http://localhost:8000/api/jobs?status=failed
```

Response:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "transactions.csv",
    "status": "completed",
    "row_count_raw": 100,
    "row_count_clean": 98,
    "created_at": "2024-12-20T10:30:00Z",
    "completed_at": "2024-12-20T10:35:15Z"
  }
]
```

---

## 4. Testing the Complete Flow

### Test 1: Local Development with Docker

1. **Start services**:
   ```bash
   docker compose up --build
   ```

2. **Wait for health** (30 seconds):
   ```bash
   curl http://localhost:8000/health
   ```

3. **Upload sample data**:
   ```bash
   curl -X POST http://localhost:8000/api/jobs/upload \
     -F "file=@data/transactions.csv"
   ```

4. **Get job ID from response**, then poll status:
   ```bash
   JOB_ID="550e8400-e29b-41d4-a716-446655440000"
   
   # Poll until completed (processing takes 10-30 seconds)
   watch -n 2 "curl http://localhost:8000/api/jobs/$JOB_ID/status"
   ```

5. **Once completed, get results**:
   ```bash
   curl http://localhost:8000/api/jobs/$JOB_ID/results | jq
   ```

6. **View in browser**:
   - Open: http://localhost:8000
   - Upload CSV via UI
   - Check status and results

### Test 2: Verify All Stages

**CSV parsing**:
- Check `/uploads/` directory for saved file
- Verify file is readable text

**Data cleaning**:
- Check database: `SELECT COUNT(*) FROM transactions`
- Verify dates are parsed correctly

**Anomaly detection**:
- Query: `SELECT COUNT(*) FROM transactions WHERE is_anomaly = true`
- Verify anomaly_reason is populated

**LLM classification**:
- Query: `SELECT DISTINCT llm_category FROM transactions`
- Should see: Food, Shopping, Travel, etc.

**Summary**:
- Query: `SELECT * FROM job_summaries WHERE job_id = '{job_id}'`
- Verify narrative is generated

### Test 3: Failure Cases

**Invalid CSV**:
```bash
echo "invalid,data" > bad.csv
curl -X POST http://localhost:8000/api/jobs/upload -F "file=@bad.csv"
# Expected: 400 Bad Request - "Missing required columns"
```

**Non-existent job**:
```bash
curl http://localhost:8000/api/jobs/invalid-uuid/status
# Expected: 404 Not Found
```

**Results before completion**:
```bash
# Immediately after upload
curl http://localhost:8000/api/jobs/$JOB_ID/results
# Expected: 400 Bad Request - "Job is not completed yet"
```

---

## 5. Monitoring & Debugging

### View Logs

```bash
# API server
docker logs api

# Celery worker
docker logs worker

# PostgreSQL
docker logs postgres

# Redis
docker logs redis
```

### Common Issues

**Worker not processing**:
```bash
# Check worker is running
docker ps | grep worker

# Check Redis connection
docker exec redis redis-cli ping

# Restart worker
docker compose restart worker
```

**Database errors**:
```bash
# Connect to database
docker exec -it postgres psql -U postgres -d transactions_db

# Check tables
\dt

# Check job status
SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1;
```

**LLM classification failing**:
- Check if `GEMINI_API_KEY` is set (optional)
- Fallback rules should still work
- Check logs for API errors

---

## 6. Performance Benchmarks

On sample data (`data/transactions.csv` with 20 transactions):

| Stage | Time | Notes |
|-------|------|-------|
| Upload | ~100ms | Network + file write |
| CSV Parsing | ~10ms | Fast text parsing |
| Data Cleaning | ~20ms | Date/amount normalization |
| Anomaly Detection | ~15ms | Statistical calculation |
| LLM Classification | ~2-5s | API call (if enabled) |
| Summary Generation | ~1s | Compute + LLM (if enabled) |
| DB Write | ~50ms | 20 transactions |
| **Total** | **~3-8s** | Depends on LLM availability |

With 1000 transactions:
- Without LLM: ~500ms
- With LLM: ~15-20s (10 batches)

---

## 7. End-to-End Success Criteria

✅ **Upload works**: File accepted, job created
✅ **Status endpoint**: Shows PENDING → PROCESSING → COMPLETED
✅ **Data cleaning**: Duplicates removed, dates normalized
✅ **Anomaly detection**: Transactions flagged correctly
✅ **Classification**: All categories assigned
✅ **Summary**: Narrative generated, metrics computed
✅ **Results**: All data retrievable via API
✅ **Error handling**: Invalid inputs rejected gracefully
✅ **Performance**: Completes in <30 seconds for typical CSVs

---

## Quick Start

```bash
# 1. Clone & setup
git clone <repo>
cd ai-transaction-pipeline

# 2. Create .env
cp .env.example .env
# (Optional) Add GEMINI_API_KEY for LLM features

# 3. Start services
docker compose up --build

# 4. Upload test data
curl -X POST http://localhost:8000/api/jobs/upload \
  -F "file=@data/transactions.csv"

# 5. Check results (substitute your job_id)
curl http://localhost:8000/api/jobs/{job_id}/status
curl http://localhost:8000/api/jobs/{job_id}/results
```

**Access UI**: http://localhost:8000
**API Docs**: http://localhost:8000/docs
