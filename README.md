# AI Transaction Processing Pipeline

An AI-powered backend system that processes financial transaction CSV files asynchronously, cleans and validates data, detects anomalies, classifies transactions using an LLM, and generates a structured summary report.

## Features

* Upload transaction CSV files
* Background job processing using Celery + Redis
* Data cleaning and normalization
* Anomaly detection
* AI-powered transaction categorization
* AI-generated spending summary
* PostgreSQL data storage
* REST APIs with FastAPI
* Dockerized setup with a single command

## Tech Stack

* FastAPI
* PostgreSQL
* Redis
* Celery
* Groq LLM API
* Docker & Docker Compose

## Project Architecture

User Upload
→ FastAPI API
→ Redis Queue
→ Celery Worker
→ PostgreSQL
→ LLM (Groq)
→ Processed Results

## Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd ai-transaction-pipeline
```

# Environment Setup

Before starting the application, create a `.env` file in the project root directory.

Add the following variables:

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/transactions_db
REDIS_URL=redis://redis:6379/0
GROQ_API_KEY=YOUR_GROQ_API_KEY_HERE

### 3. Start the application

```bash
docker compose up --build
```

The application will automatically start:

* FastAPI API
* PostgreSQL
* Redis
* Celery Worker

## Access URLs

API Documentation:

```text
http://localhost:8000/docs
```

Application:

```text
http://localhost:8000
```

## API Endpoints

### Upload CSV

```http
POST /api/jobs/upload
```

Uploads a CSV file and starts background processing.

### Check Job Status

```http
GET /api/jobs/{job_id}/status
```

Returns the current job status.

### Get Results

```http
GET /api/jobs/{job_id}/results
```

Returns processed transactions, anomalies, category breakdown, and AI summary.

### List Jobs

```http
GET /api/jobs
```

Returns all submitted jobs.

## Processing Pipeline

### 1. Data Cleaning

* Normalize date formats
* Remove currency symbols
* Standardize status values
* Fill missing categories
* Remove duplicate records

### 2. Anomaly Detection

* Transactions greater than 3× account median
* Domestic merchants using USD currency

### 3. AI Classification

Missing transaction categories are classified into:

* Food
* Shopping
* Travel
* Transport
* Utilities
* Cash Withdrawal
* Entertainment
* Other

### 4. AI Summary Generation

Generates:

* Total spend by currency
* Top merchants
* Anomaly count
* Spending narrative
* Risk level

## Design Decisions

* Celery is used to keep CSV processing asynchronous and non-blocking.
* Redis acts as the message broker for background jobs.
* PostgreSQL stores jobs, transactions, anomalies, and summaries.
* Docker Compose provides a reproducible one-command setup.
* LLM failures are handled gracefully and do not stop the entire pipeline.

## Submission Notes

This project was built as part of the Backend + DevOps Internship Assignment.

The repository is fully containerized and can be started using:

```bash
docker compose up --build
```

No manual PostgreSQL or Redis installation is required.
