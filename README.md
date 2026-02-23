# EEG Monitoring Pipeline

An EEG data pipeline built to demonstrate how software systems can support epilepsy monitoring in clinical settings. This project models the flow of EEG data — from device capture through ingestion, storage, retrieval, and interactive visualisation — using the CHB-MIT Scalp EEG Database from PhysioNet.

Epilepsy affects over 50 million people worldwide, making it one of the most common neurological conditions. Clinicians rely on continuous EEG recordings to identify seizure patterns, but raw EEG data is dense — a single hour of 23-channel recording at 256 Hz produces over 21 million data points. Managing this volume efficiently requires careful data pipeline design.

## Architecture

```
┌─────────────────────┐
│   EEG Simulator     │  Reads EDF files, streams 1-second chunks
│   (Python script)   │  Simulates device data stream
└────────┬────────────┘
         │ POST /api/ingest/ (JSON)
         ▼
┌─────────────────────┐
│   Ingestion API     │  Validates, deduplicates, expands chunks
│   (FastAPI)         │  Logs every ingestion with SHA-256 checksum
└────────┬────────────┘
         │ SQLAlchemy ORM
         ▼
┌─────────────────────┐
│   PostgreSQL 16     │  Indexed on (patient, recording, timestamp)
│   (Docker)          │  Stores raw sample data
└────────┬────────────┘
         │ SQLAlchemy query → JSON
         ▼
┌─────────────────────┐
│   Query API         │  GET /api/eeg/{patient_id}/recordings/...
│   (FastAPI)         │  Returns windowed EEG data
└────────┬────────────┘
         │ fetch() with CORS
         ▼
┌─────────────────────┐
│   React Dashboard   │  Interactive viewer with recording selector
│   (Vite + React)    │  TypeScript, component-based UI
└─────────────────────┘
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Package Manager | uv | Fast, modern Python dependency management |
| Simulator | Python + MNE | Load and stream real EEG data from EDF files |
| API Framework | FastAPI | Auto-generated OpenAPI docs, dependency injection |
| ORM | SQLAlchemy 2.0 | Python-to-SQL mapping, type-annotated models |
| Database | PostgreSQL 16 (Alpine) | Relational storage with composite indexes |
| Validation | Pydantic | Request/response schema validation |
| Containerisation | Docker Compose | Reproducible multi-service environment |
| Frontend | React 19 + TypeScript | Type-safe interactive dashboard |
| Build Tool | Vite | Fast HMR, API proxy for development |

## Project Structure

```
seer_medical/
├── pipeline/                    # Backend Python package
│   ├── db.py                    # SQLAlchemy engine, session, Base, init_db()
│   ├── models.py                # ORM models: EegSample, IngestionLog
│   ├── schemas.py               # Pydantic: IngestRequest, IngestResponse
│   ├── api.py                   # FastAPI app with ingest + query routers
│   └── simulator.py             # EEG device simulator (EDF → API)
├── frontend/                    # React + TypeScript app
│   ├── src/
│   │   ├── components/
│   │   │   └── dashboard.tsx    # Main dashboard component
│   │   ├── api.ts               # API client (fetch wrappers)
│   │   ├── types.ts             # TypeScript interfaces
│   │   ├── App.tsx              # Root component
│   │   ├── App.css              # Dashboard styles
│   │   └── index.css            # Global styles
│   ├── vite.config.ts           # Vite + API proxy config
│   └── package.json
├── docker-compose.yml           # PostgreSQL + FastAPI services
├── Dockerfile                   # Backend container (Python 3.11-slim)
├── pyproject.toml               # Python dependencies (uv)
├── .env.template                # Environment variable template
└── tests/
    └── api_ingest.http          # HTTP test cases (VS Code REST Client)
```

## Data Processing

### EEG Simulator (`pipeline/simulator.py`)

The simulator reads EDF files from the CHB-MIT dataset and sends them to the ingestion API in 1-second chunks, simulating a device data stream. 

**Data flow:**
1. **Load** — `mne.io.read_raw_edf()` reads the EDF file into memory (23 channels × 921,600 samples per hour)
2. **Chunk** — The recording is sliced into 1-second windows (each chunk: 23 channels × 256 samples)
3. **Stream** — Each chunk is POST'd as JSON to `/api/ingest/` with metadata (recording ID, chunk index, timestamp)

```
EDF file (1 hour) → 3,600 chunks → 3,600 POST requests → 3,600 × 5,888 = 21,196,800 DB rows
```

The simulator supports `limit` and `delay` parameters for controlled testing. Running with `limit=10` ingests 10 seconds of data per file.

### Data Model (`pipeline/models.py`)

**EegSample** — One row per sample point (row-per-sample storage):
| Column | Type | Description |
|--------|------|-------------|
| `patient_id` | Text | Patient identifier (e.g., `chb01`) |
| `recording_id` | Text | Source file name (e.g., `chb01_03.edf`) |
| `channel` | Text | Electrode name (e.g., `FP1-F7`) |
| `timestamp_sec` | Double | Time offset from recording start |
| `value_uv` | Double | Voltage in microvolts |
| `ingested_at` | DateTime | UTC ingestion timestamp |

**Indexes** for query performance:
- `(patient_id, recording_id, timestamp_sec)` — time-range queries
- `(patient_id, recording_id, channel, timestamp_sec)` — per-channel queries

**IngestionLog** — Ingestion Log for every ingested chunk:
| Column | Type | Description |
|--------|------|-------------|
| `recording_id` | Text | Source recording |
| `chunk_start_sec` | Double | Chunk time window start |
| `chunk_end_sec` | Double | Chunk time window end |
| `num_samples` | Integer | Total samples in chunk |
| `checksum` | String(64) | SHA-256 hash of chunk data |

The ingestion endpoint uses the log for **duplicate detection** — if a chunk with the same `recording_id` and `chunk_start_sec` already exists, it returns `"duplicate"` instead of re-inserting.

## Data Ingestion (`pipeline/api.py`)

The ingestion endpoint expands each chunk into individual sample rows:

```
POST /api/ingest/
{
  "recording_id": "chb01_03.edf",
  "chunk_index": 0,
  "channels": ["FP1-F7", "F7-T7", ...],     // 23 channels
  "data": [[1.23, -4.56, ...], ...],          // 23 × 256 values
  "timestamp": 1708300000.0
}
```

**Processing steps:**
1. Check `IngestionLog` for duplicate chunk
2. Expand 2D array into individual `EegSample` rows (23 × 256 = 5,888 rows per chunk)
3. Derive `patient_id` from `recording_id` (e.g., `chb01_03.edf` → `chb01`)
4. Compute `timestamp_sec` for each sample: `chunk_index + sample_idx / sfreq`
5. Calculate SHA-256 checksum of chunk data
6. Bulk insert samples + ingestion log entry in a single transaction

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ingest/` | Ingest a 1-second chunk of multi-channel EEG data |
| `GET` | `/api/eeg/{patient_id}/recordings` | Patient overview: total samples, channel list |
| `GET` | `/api/eeg/{patient_id}/recordings/{recording_id}/summary` | Recording metadata |
| `GET` | `/api/eeg/{patient_id}/recordings/{recording_id}/data?start_sec=0&end_sec=1` | Windowed EEG samples |
| `GET` | `/health` | API health check |

API documentation is auto-generated at `http://localhost:8000/docs` (Swagger UI).

## Backend Configuration

### Docker Compose

Two services configured via `docker-compose.yml`:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `db` | `postgres:16-alpine` | 5432 | EEG data storage |
| `backend` | Custom (Dockerfile) | 8000 | FastAPI application |

The backend container connects to PostgreSQL using Docker's internal DNS (`db:5432`), while the host machine accesses both services via mapped ports.

### Database Connection (`pipeline/db.py`)

- **Engine**: SQLAlchemy with `pool_pre_ping=True` for connection health checking
- **Session management**: FastAPI dependency injection via `get_db()` generator
- **Table creation**: `init_db()` runs on application startup via FastAPI lifespan

### CORS

The API includes CORS middleware allowing requests from `http://localhost:5173` (Vite dev server), enabling the React frontend to call the backend directly during development.

## Frontend (`frontend/`)

Built with React 19, TypeScript, and Vite. No additional UI libraries — plain CSS for a clean, minimal interface.

### Key files:
- **`api.ts`** — Typed fetch wrappers for all backend endpoints
- **`types.ts`** — TypeScript interfaces matching backend response schemas
- **`dashboard.tsx`** — Main component: health indicator, patient overview, recording selector (43 files), sample data table

### API Communication

During development, the frontend uses environment variables (`VITE_API_URL`) to connect to the backend. CORS is configured on the FastAPI side to allow cross-origin requests from the Vite dev server.

## Prerequisites

- [Docker](https://www.docker.com/) (for PostgreSQL and backend)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) >= 18 (for frontend)

## Getting Started

```bash
# Clone the repository
git clone <repo-url>
cd seer-medical

# Start PostgreSQL + backend
docker compose up -d --build

# Install Python dependencies
uv sync

# Ingest EEG data (10 seconds from each of 42 recordings)
uv run python pipeline/simulator.py

# Start the frontend
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173` to view the dashboard.

### Running backend locally (without Docker)

```bash
# Start only PostgreSQL in Docker
docker compose up -d db

# Run FastAPI directly
uv run uvicorn pipeline.api:app --reload
```

## Data

This project uses the [CHB-MIT Scalp EEG Database](https://physionet.org/content/chbmit/1.0.0/) from PhysioNet. Only the `chb01` patient directory is required (~350 MB). The data is not included in this repository — download it separately and place it at:

```
chb-mit/physionet.org/files/chbmit/1.0.0/chb01/
```

### Dataset characteristics
- **Patient**: chb01 (42 recordings)
- **Channels**: 23 EEG electrodes
- **Sampling rate**: 256 Hz
- **Duration**: ~1 hour per recording
- **Seizures**: 7 annotated seizure events across multiple files
