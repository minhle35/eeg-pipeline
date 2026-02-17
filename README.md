# EEG Monitoring Pipeline

A full-stack EEG data pipeline built to demonstrate how scalable software systems can support real-time epilepsy monitoring in clinical settings. This project simulates the end-to-end journey of electroencephalogram (EEG) data — from device capture through ingestion, storage, retrieval, and interactive visualisation — using the CHB-MIT Scalp EEG dataset from PhysioNet.

Epilepsy affects over 50 million people worldwide, making it one of the most common neurological conditions. Clinicians rely on continuous EEG recordings to identify seizure patterns, but raw EEG data is dense — a single hour of 23-channel recording at 256 Hz produces over 21 million data points. Managing this volume efficiently while keeping query latency low enough for real-time clinical review is a core engineering challenge in digital health.

This project addresses that challenge by building a local pipeline that mirrors production-grade architecture. An EEG simulator streams chunked data to a FastAPI ingestion API, which writes to a PostgreSQL database optimised for time-series queries. A separate query API serves windowed EEG segments to an interactive Dash/Plotly viewer, where clinicians can navigate recordings, toggle channels, inspect spectrograms, and jump directly to seizure events. The system includes latency benchmarking to measure insert throughput and query performance under realistic data volumes.

The tech stack — Python, FastAPI, PostgreSQL, SQLAlchemy, Docker, Dash, and Plotly — was chosen to balance simplicity with real-world relevance. Every architectural decision, from append-only storage to chunked retrieval, reflects patterns used in medical data systems where data integrity, auditability, and performance are non-negotiable.

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
| Package Manager | uv | Fast, modern Python dependency management |
| Simulator | Python + MNE | Industry-standard EDF/EEG library |
| API | FastAPI | Async, fast, auto-generates OpenAPI docs |
| ORM | SQLAlchemy 2.0 | Pythonic database layer, modern mapped columns |
| Database | PostgreSQL 16 (Docker) | Industry standard, robust, free |
| Containerisation | Docker Compose | Reproducible database setup |
| Viewer | Dash + Plotly | Interactive EEG visualisation with WebGL |
| Benchmarking | Python + tabulate | Measure insert/query performance |

## Project Structure

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
├── pyproject.toml         # Dependencies (managed by uv)
├── uv.lock                # Lockfile (auto-generated)
└── .env                   # Database credentials (not committed)
```

## Prerequisites

- [Docker](https://www.docker.com/) (for PostgreSQL)
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Getting Started

```bash
# Clone the repository
git clone <repo-url>
cd seer-medical

# Install dependencies
uv sync

# Start PostgreSQL
docker compose up -d

# Create database tables
uv run python -c "from pipeline.db import init_db; init_db()"

# Start the API server
uv run uvicorn pipeline.api:app --reload

# In a separate terminal — run the EEG viewer
uv run python eeg_viewer.py
```

## Data

This project uses the [CHB-MIT Scalp EEG Database](https://physionet.org/content/chbmit/1.0.0/) from PhysioNet. Only the `chb01` patient directory is required (~350 MB). The data is not included in this repository — download it separately and place it at `chb-mit/physionet.org/files/chbmit/1.0.0/chb01/`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingest` | Ingest a 1-second chunk of multi-channel EEG data |
| `GET` | `/eeg` | Query windowed EEG data by patient, recording, and time range |
| `GET` | `/recordings` | List ingested recordings for a patient |
