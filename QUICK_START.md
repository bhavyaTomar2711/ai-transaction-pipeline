# Quick Start Guide

Get the AI Transaction Pipeline running in 5 minutes!

---

## 🚀 Option 1: Local Development (Fastest)

### Step 1: Download & Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd ai-transaction-pipeline

# Copy environment template
cp .env.example .env
```

### Step 2: (Optional) Get Gemini API Key
1. Visit: **https://aistudio.google.com/app/apikey**
2. Click **"Create API Key in new project"**
3. Copy the key
4. Edit `.env` and add:
   ```
   GEMINI_API_KEY=<paste-your-key-here>
   ```

### Step 3: Start Services
```bash
docker compose up --build
```

Wait 30 seconds for services to start...

### Step 4: Open in Browser
```
http://localhost:8000
```

### Step 5: Upload a CSV
1. Click "Upload CSV"
2. Select `data/transactions.csv` (included in repo)
3. Wait 3-8 seconds for processing
4. View results!

**That's it! 🎉**

---

## 🌐 Option 2: Production Deployment (Supabase + Redis Cloud)

### Prerequisites
- Supabase account (free): https://supabase.com
- Redis Cloud account (free): https://redis.com/try-free/

### Step 1: Set Up Supabase
1. Go to https://supabase.com and sign up
2. Create a new project
3. Go to **Settings → Database → Connection string**
4. Copy the connection string

### Step 2: Set Up Redis Cloud
1. Go to https://redis.com/try-free/ and sign up
2. Create a free database
3. Copy your Redis connection string

### Step 3: Configure .env
```bash
cp .env.example .env
```

Edit `.env` and update:
```
DATABASE_URL=<your-supabase-connection-string>
REDIS_URL=<your-redis-cloud-connection-string>
GEMINI_API_KEY=<optional-api-key>
```

### Step 4: Create Database Schema
1. Copy contents of `supabase_migration.sql`
2. In Supabase: Go to **SQL Editor → New Query**
3. Paste and execute the SQL

### Step 5: Deploy
```bash
docker compose up -d
```

Your app is now live! Access it at your deployed URL.

---

## 🔑 Getting Your Gemini API Key (2 minutes)

### Why Get It?
- ✨ AI-powered transaction categorization
- 📊 Intelligent spending narratives
- 🎯 Better risk assessment
- Works without it too! (uses rule-based fallback)

### How to Get It:
1. **Open**: https://aistudio.google.com/app/apikey
2. **Click**: "Create API Key in new project"
3. **Copy**: Your new API key
4. **Paste**: Into `.env` as `GEMINI_API_KEY=<your-key>`
5. **Restart**: `docker compose restart api worker`

**Free tier**: 15 requests per minute (plenty for testing!)

---

## 📊 Test the API

### Upload a CSV
```bash
curl -X POST http://localhost:8000/api/jobs/upload \
  -F "file=@data/transactions.csv"
```

**Response** (save the `job_id`):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "File uploaded successfully. Processing started."
}
```

### Check Status
```bash
curl http://localhost:8000/api/jobs/550e8400-e29b-41d4-a716-446655440000/status
```

### Get Results (when completed)
```bash
curl http://localhost:8000/api/jobs/550e8400-e29b-41d4-a716-446655440000/results | jq
```

### View API Documentation
```
http://localhost:8000/docs
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `Connection refused` to database | Check DATABASE_URL in .env, verify PostgreSQL running |
| `Connection refused` to Redis | Check REDIS_URL in .env, verify Redis running |
| Worker not processing | `docker compose restart worker` |
| CSV upload fails | Ensure CSV has these columns: `txn_id, date, merchant, amount, currency, status, category, account_id, notes` |
| "GEMINI_API_KEY not provided" warning | This is fine! System will use rule-based classification. Optional: Add key from aistudio.google.com |

---

## 📚 Documentation

- **Full Setup Guide**: `API_KEYS_SETUP.md`
- **Pipeline Details**: `END_TO_END_FLOW.md`
- **Project Overview**: `README.md`
- **What's Completed**: `COMPLETION_SUMMARY.md`

---

## ⚡ Quick Commands

```bash
# Start everything
docker compose up --build

# Stop everything
docker compose down

# View logs
docker compose logs -f api

# Restart a service
docker compose restart worker

# Connect to database
docker exec -it postgres psql -U postgres -d transactions_db

# Test Redis
docker exec redis redis-cli ping
```

---

## 🎯 Next Steps

1. ✅ Run locally with `docker compose up --build`
2. ✅ Upload sample CSV via UI at http://localhost:8000
3. ✅ Check results via `/api/jobs/{job_id}/results`
4. ✅ (Optional) Add GEMINI_API_KEY for LLM features
5. ✅ Deploy to production (Supabase + Redis Cloud)

---

## 🎓 Understanding the Pipeline

```
CSV File
  ↓ (Upload)
Parse & Validate
  ↓
Clean Data (normalize dates, amounts, deduplicate)
  ↓
Detect Anomalies (statistical outliers, currency mismatches)
  ↓
Classify Transactions (LLM or rule-based)
  ↓
Generate Summary (totals, narrative, risk assessment)
  ↓
Store in Database
  ↓
Return Results via API
```

**Processing time**: 3-8 seconds for typical CSV files

---

## 📞 Support

For detailed information, see:
- `API_KEYS_SETUP.md` - Configuration and deployment
- `END_TO_END_FLOW.md` - Complete pipeline explanation
- `README.md` - General overview
- `COMPLETION_SUMMARY.md` - Project status

---

**Ready to get started? Run:**
```bash
docker compose up --build
```

**Then visit:** http://localhost:8000 🚀
