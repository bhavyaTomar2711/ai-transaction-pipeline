# AI Transaction Pipeline

A full-stack application that processes dirty financial CSV data through an AI-powered pipeline — cleaning, anomaly detection, LLM classification, and narrative summary generation.

## Architecture

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Frontend │────▶│ FastAPI  │────▶│  Celery  │────▶│  Gemini  │
│  (Static) │◀────│   API    │◀────│  Worker  │◀────│ 1.5 Flash│
└──────────┘     └────┬─────┘     └────┬─────┘     └──────────┘
                      │                │
                 ┌────▼─────┐     ┌────▼─────┐
                 │PostgreSQL│     │   Redis   │
                 │    DB    │     │  Broker   │
                 └──────────┘     └──────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI |
| ORM | SQLAlchemy |
| Database | PostgreSQL 16 |
| Job Queue | Celery + Redis |
| LLM | Google Gemini 1.5 Flash |
| Containerization | Docker Compose |
| Frontend | Vanilla HTML/CSS/JS |

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- (Optional) Google Gemini API key for LLM features

### Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd ai-transaction-pipeline
   ```

2. **Configure environment** (optional — for LLM features)
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

3. **Start all services**
   ```bash
   docker compose up --build
   ```

4. **Access the application**
   - Frontend UI: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## API Endpoints

### `POST /api/jobs/upload`
Upload a CSV file for processing.
```bash
curl -X POST http://localhost:8000/api/jobs/upload \
  -F "file=@data/transactions.csv"
```

### `GET /api/jobs/{job_id}/status`
Check job processing status.
```bash
curl http://localhost:8000/api/jobs/{job_id}/status
```

### `GET /api/jobs/{job_id}/results`
Get full results (only when status=completed).
```bash
curl http://localhost:8000/api/jobs/{job_id}/results
```

### `GET /api/jobs`
List all jobs. Supports `?status=` filter.
```bash
curl http://localhost:8000/api/jobs
curl http://localhost:8000/api/jobs?status=completed
```

## Processing Pipeline

1. **Data Cleaning** — Date normalization, amount parsing, status uppercasing, deduplication
2. **Anomaly Detection** — Statistical outliers (3x median), currency mismatches, suspicious flags
3. **LLM Classification** — Batch categorization via Gemini (with rule-based fallback)
4. **Narrative Summary** — AI-generated spending analysis with risk assessment

## CSV Format

The input CSV should contain these columns:
```
txn_id, date, merchant, amount, currency, status, category, account_id, notes
```

A sample file is included at `data/transactions.csv`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@postgres:5432/transactions_db` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `GEMINI_API_KEY` | _(empty)_ | Google Gemini API key (optional — falls back to rules) |

## Project Structure

```
ai-transaction-pipeline/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings management
│   ├── database.py          # SQLAlchemy setup
│   ├── models.py            # ORM models
│   ├── schemas.py           # Pydantic schemas
│   ├── api/
│   │   └── jobs.py          # API endpoints
│   ├── services/
│   │   ├── csv_parser.py    # CSV validation & parsing
│   │   ├── data_cleaner.py  # Data normalization
│   │   ├── anomaly_detector.py  # Anomaly flagging
│   │   ├── llm_classifier.py   # LLM categorization
│   │   └── llm_summarizer.py   # Narrative generation
│   └── worker/
│       ├── celery_app.py    # Celery configuration
│       └── tasks.py         # Processing pipeline task
├── frontend/                # Premium UI
├── data/
│   └── transactions.csv     # Sample data
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
