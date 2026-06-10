# API Keys & Setup Guide

This document explains the API keys needed and how to set them up for the AI Transaction Pipeline.

## Summary

| Service | API Key | Required | Purpose |
|---------|---------|----------|---------|
| Google Gemini | `GEMINI_API_KEY` | ❌ Optional | LLM classification & narrative generation |
| PostgreSQL | N/A (connection string) | ✅ Required | Database storage |
| Redis | N/A (connection string) | ✅ Required | Job queue broker |

---

## 1. Google Gemini API (Optional)

### What it does:
- **LLM Classification**: Intelligently categorizes transactions (Food, Shopping, Travel, etc.)
- **Narrative Generation**: Creates spending analysis summaries
- **Risk Assessment**: Evaluates financial risk levels

### Without this API key:
The pipeline will still work! It automatically falls back to:
- Rule-based merchant classification
- Local narrative generation
- Statistical risk assessment

### How to get the key:

1. Visit: https://aistudio.google.com/app/apikey
2. Click **"Create API Key"**
3. Select or create a Google Cloud project
4. Copy the generated API key
5. Add to `.env` file:
   ```
   GEMINI_API_KEY=your_key_here_paste_the_long_string
   ```

### Model used:
- **Gemini 1.5 Flash** (fast, cost-effective)
- Free tier: 15 requests per minute

---

## 2. PostgreSQL Database

### Local Development (Docker Compose):
- **Host**: `postgres` (Docker container)
- **Port**: `5432`
- **User**: `postgres`
- **Password**: `postgres`
- **Database**: `transactions_db`
- **Connection string**: 
  ```
  postgresql://postgres:postgres@postgres:5432/transactions_db
  ```

### Production (Supabase):
1. Sign up: https://supabase.com
2. Create a new project
3. Go to: **Settings → Database → Connection string**
4. Copy the connection string
5. Update `.env` file:
   ```
   DATABASE_URL=postgresql://[user]:[password]@[host]:[port]/[database]
   ```
6. Run the migration: See `supabase_migration.sql`

### Schema setup:
The database schema is automatically created when the FastAPI app starts. To manually run the schema:
1. Copy contents of `supabase_migration.sql`
2. In Supabase: Go to **SQL Editor → New Query**
3. Paste and run the SQL

---

## 3. Redis (Job Broker)

### Local Development (Docker Compose):
- **Host**: `redis` (Docker container)
- **Port**: `6379`
- **Connection string**:
  ```
  redis://redis:6379/0
  ```

### Production (Cloud Redis):
Options:
- **Redis Cloud**: https://redis.com/try-free/
- **Upstash**: https://upstash.com
- **AWS ElastiCache**: https://aws.amazon.com/elasticache/

Example Redis Cloud setup:
1. Create a free database
2. Get connection string: `redis://:password@host:port/0`
3. Update `.env`:
   ```
   REDIS_URL=redis://:your_password@your_host.redis.cloud:12345/0
   ```

---

## Setup Checklist

### For Local Development:
- [ ] Clone repository
- [ ] Create `.env` file (copy from `.env.example`)
- [ ] (Optional) Add `GEMINI_API_KEY` for LLM features
- [ ] Run: `docker compose up --build`
- [ ] Access: http://localhost:8000

### For Production (Supabase + Cloud Redis):
- [ ] Create Supabase project
- [ ] Copy PostgreSQL connection string to `.env`
- [ ] Create Redis Cloud instance
- [ ] Copy Redis connection string to `.env`
- [ ] (Recommended) Add `GEMINI_API_KEY` to `.env`
- [ ] Deploy containers with new `.env`
- [ ] Run `supabase_migration.sql` in Supabase SQL Editor
- [ ] Test: Upload a CSV file and check processing

---

## Testing the Setup

### 1. Check Health:
```bash
curl http://localhost:8000/health
```

### 2. Upload Test CSV:
```bash
curl -X POST http://localhost:8000/api/jobs/upload \
  -F "file=@data/transactions.csv"
```

### 3. Check Job Status:
```bash
curl http://localhost:8000/api/jobs/{job_id}/status
```

### 4. Get Results:
```bash
curl http://localhost:8000/api/jobs/{job_id}/results
```

---

## Environment Variables Reference

```bash
# Required for any setup
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/transactions_db
REDIS_URL=redis://redis:6379/0

# Optional (recommended)
GEMINI_API_KEY=

# Optional (defaults shown)
UPLOAD_DIR=uploads
LLM_BATCH_SIZE=10
LLM_MAX_RETRIES=3
LLM_RETRY_BASE_DELAY=2.0
ANOMALY_MULTIPLIER=3.0
```

---

## Troubleshooting

### "GEMINI_API_KEY not provided"
- This is just a warning. The pipeline will use rule-based fallbacks.
- If you want LLM features, get a key from: https://aistudio.google.com/app/apikey

### "Connection refused to PostgreSQL"
- Verify DATABASE_URL is correct
- For Docker: Use `postgres` as hostname (not `localhost`)
- For Supabase: Check the connection string from dashboard

### "Connection refused to Redis"
- Verify REDIS_URL is correct
- For Docker: Use `redis` as hostname (not `localhost`)
- Check Redis is running: `redis-cli ping`

### "502 Bad Gateway" when uploading
- Celery worker may be down
- Check worker logs: `docker logs ai-transaction-pipeline-worker-1`
- Restart: `docker compose restart worker`

---

## Support

For issues, check:
1. Application logs: `docker logs <container_name>`
2. API docs: http://localhost:8000/docs
3. README.md in project root
