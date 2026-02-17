# EEG Data Pipeline — Project Plan

## What This Is

A backend data pipeline that mirrors the infrastructure behind clinical EEG monitoring systems. The system splits EEG data processing into independent services that communicate over APIs — the same architecture used in production medical device platforms.

## Why It Matters

Long-term ambulatory EEG monitoring (home-based, multi-day) generates serious data volumes:

| Parameter | Value |
|-----------|-------|
| Channels | 23 (bipolar montage) |
| Sampling rate | 256 Hz |
| Duration | 24 hours per recording |
| Samples/day | 23 x 256 x 86,400 = **509 million** |
| Storage/day | ~3.8 GB (float64) |

You can't load this into memory and hand it to a frontend. Real systems need:

- **Streaming ingestion** — data arrives in real-time chunks from a wearable device
- **Efficient storage** — indexed time-series data, not flat files
- **Chunked retrieval** — clinicians view 10-second windows, not entire recordings
- **Data integrity** — medical records are immutable, auditable, and versioned

This prototype demonstrates all four.

## Architecture

```
┌─────────────────────┐
│   EEG Simulator     │  Reads EDF files, streams 1-second chunks
│   (Python script)   │  Mimics wearable device firmware
└────────┬────────────┘
         │ POST /ingest (JSON)
         ▼
┌─────────────────────┐
│   Ingestion API     │  Validates, timestamps, stores
│   (FastAPI)         │  Logs every ingestion event
└────────┬────────────┘
         │ SQLAlchemy ORM
         ▼
┌─────────────────────┐
│   PostgreSQL        │  Indexed on (patient_id, timestamp)
│   (Docker)          │  Append-only, immutable raw data
└────────┬────────────┘
         │ SQLAlchemy query → JSON
         ▼
┌─────────────────────┐
│   Query API         │  GET /eeg?patient_id=...&start=...&end=...
│   (FastAPI)         │  Returns windowed EEG data
└────────┬────────────┘
         │ JSON response
         ▼
┌─────────────────────┐
│   EEG Viewer        │  Interactive Dash app for clinical review
│   (Dash/Plotly)     │  Calls Query API for data
└─────────────────────┘
```

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Simulator | Python + MNE | Industry-standard EDF/EEG library |
| API | FastAPI | Async, fast, auto-generates OpenAPI docs |
| ORM | SQLAlchemy 2.0 | Pythonic database layer, modern mapped columns |
| Database | PostgreSQL 16 (Docker) | Industry standard, robust, free |
| Containerisation | Docker Compose | Reproducible database setup |
| Viewer | Dash + Plotly | Interactive EEG visualisation with WebGL |
| Benchmarking | Python + tabulate | Measure insert/query performance |

---

## Steps

### Step 1 — Docker + Project Structure

Set up PostgreSQL in Docker and create the project skeleton.

**docker-compose.yml:**
- PostgreSQL 16 Alpine container
- Credentials loaded from `.env`
- Persistent volume for data

**Project layout:**
```
seer_medical/
├── pipeline/
│   ├── __init__.py
│   ├── db.py              # SQLAlchemy engine, session, Base
│   ├── models.py          # ORM models (EegSample, IngestionLog)
│   ├── simulator.py       # EEG device simulator
│   ├── api.py             # FastAPI app (ingest + query)
│   └── benchmark.py       # Latency measurement script
├── eeg_viewer.py          # Dash/Plotly interactive viewer
├── read_seizures.py       # CHB-MIT seizure annotation parser
├── docker-compose.yml
├── requirements.txt
├── .env
└── .gitignore
```

**Start the database:**
```bash
docker compose up -d
```

### Step 2 — SQLAlchemy Models + Database Schema

Define the database schema entirely in Python using SQLAlchemy 2.0 ORM — no raw SQL files.

**`pipeline/db.py`** — engine, session factory, `init_db()`:
- Reads `DATABASE_URL` from environment
- Provides `get_db()` dependency for FastAPI
- `init_db()` calls `Base.metadata.create_all()` to create tables

**`pipeline/models.py`** — two ORM models:

**`EegSample`** — the raw EEG data:
- `id` (BigInteger, primary key)
- `patient_id`, `recording_id`, `channel` (Text)
- `timestamp_sec`, `value_uv` (Double)
- `ingested_at` (datetime, auto-set to UTC now)
- Indexes on `(patient_id, recording_id, timestamp_sec)` and `(patient_id, recording_id, channel, timestamp_sec)`

**`IngestionLog`** — audit trail:
- `id` (BigInteger, primary key)
- `patient_id`, `recording_id` (Text)
- `chunk_start_sec`, `chunk_end_sec` (Double, nullable)
- `num_samples` (Integer, nullable)
- `checksum` (String, nullable)
- `ingested_at` (datetime, auto-set to UTC now)

Key design decisions:
- Append-only (no UPDATE or DELETE on EegSample)
- Every ingestion event is logged with a SHA-256 checksum
- Composite indexes for fast windowed queries
- Tables created programmatically via `init_db()`, not SQL scripts

**Verify:**
```bash
docker compose up -d
python -c "from pipeline.db import init_db; init_db()"
```

### Step 3 — Build the EEG Simulator

`pipeline/simulator.py` — reads an EDF file and POSTs 1-second chunks to the ingestion API.

What it does:
1. Load an EDF file using MNE
2. Split data into 1-second windows (256 samples per channel)
3. For each window, POST a JSON payload to `http://localhost:8000/ingest`
4. Payload contains: patient_id, recording_id, channel names, timestamp range, sample values
5. Add a small `time.sleep(0.05)` between chunks to simulate real-time (but faster)

This mimics what a Seer wearable device does — it doesn't send the whole recording at once, it streams continuously.

### Step 4 — Build the FastAPI Endpoints

`pipeline/api.py` — FastAPI app with ingest and query endpoints. Uses SQLAlchemy ORM for all database operations.

**Ingest endpoint:**
```
POST /ingest
```
- Receives a JSON chunk (1 second of multi-channel EEG)
- Validates via Pydantic schemas
- Computes a SHA-256 checksum of the payload
- Bulk-inserts `EegSample` rows via SQLAlchemy session
- Creates an `IngestionLog` entry
- Returns 201 Created

**Query endpoint:**
```
GET /eeg?patient_id=chb01&recording_id=chb01_03.edf&start=2996&end=3006
```
- Queries `EegSample` using SQLAlchemy filters for the requested time window
- Returns JSON with channels as keys and arrays of {timestamp, value} pairs
- This is what the Dash viewer will call

**Metadata endpoint:**
```
GET /recordings?patient_id=chb01
```
- Returns list of ingested recordings, their durations, channel counts

**App startup:**
- Calls `init_db()` on startup to ensure tables exist

### Step 5 — Build the EEG Viewer

`eeg_viewer.py` — interactive Dash/Plotly web app for clinical EEG review.

The viewer calls the Query API for data:
```python
response = httpx.get(f"http://localhost:8000/eeg?patient_id=chb01&recording_id={filename}&start={t_start}&end={t_end}")
data = response.json()
```

Features:
- Stacked 23-channel EEG waveform display (WebGL via `go.Scattergl`)
- Seizure period highlighting (red shading)
- Time window navigation (5s/10s/30s/60s) with slider
- Channel toggle (show/hide individual channels)
- Spectrogram display (0–70 Hz) for selected channel
- Seizure jump buttons for quick navigation to seizure onset

### Step 6 — Benchmark

`pipeline/benchmark.py` — measure real performance numbers.

**Insert benchmarks:**
- Time how long it takes to ingest one full recording (3600 chunks)
- Calculate samples/second throughput

**Query benchmarks:**
- Query different window sizes: 1s, 5s, 10s, 30s, 60s
- Measure latency for each
- Test with 1 recording loaded vs 10 recordings loaded

**Produce a results table:**

| Operation | Window | Latency | Notes |
|-----------|--------|---------|-------|
| Query | 1 sec | ? ms | Single channel |
| Query | 10 sec | ? ms | All 23 channels |
| Query | 60 sec | ? ms | All 23 channels |
| Ingest | 1 chunk | ? ms | 23 ch x 256 samples |
| Ingest | Full file | ? sec | 3600 chunks |

### Step 7 — Technical Discussion

Add a section to the README covering tradeoffs and production considerations:

**Storage: Row-per-sample vs binary blobs**
- We used row-per-sample (one row = one channel at one timestamp) for queryability
- In production, you'd likely store compressed binary chunks (e.g., 1-second blocks) for 10-100x storage reduction
- Discuss the tradeoff: fine-grained queries vs storage efficiency

**Write-heavy vs read-heavy**
- Ingestion is write-heavy (continuous streaming from device)
- Viewer is read-heavy (clinician scrubbing through recording)
- In production: separate write and read replicas, or use a TSDB like TimescaleDB

**Immutability and audit**
- Raw EEG data must never be modified after ingestion (medical regulations)
- Our append-only schema + IngestionLog enforces this
- If you need to reprocess data, store results in a separate table with a processing version

**What would break at scale**
- Row-per-sample won't scale past ~10 patients without partitioning
- Need to partition by patient_id and time range
- Need connection pooling for concurrent clinician sessions
- Need a CDN or caching layer for frequently-viewed seizure epochs

---

## Order of Implementation

| # | Task | Output |
|---|------|--------|
| 1 | Docker + project structure | `docker-compose.yml`, `pipeline/` directory, `.env` |
| 2 | SQLAlchemy models + schema | `db.py`, `models.py`, tables created via `init_db()` |
| 3 | EEG simulator | `simulator.py` streams one EDF file to API |
| 4 | FastAPI endpoints | `POST /ingest`, `GET /eeg`, `GET /recordings` |
| 5 | Dash EEG viewer | `eeg_viewer.py` reads from Query API |
| 6 | Benchmarks | Latency table with real numbers |
| 7 | Technical writeup | README with architecture, decisions, tradeoffs |
