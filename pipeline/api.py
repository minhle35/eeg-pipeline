# FastAPI ingestion + query endpoints — Step 4

from fastapi import FastAPI, Depends, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
import hashlib
import json

from pipeline.db import get_db, init_db
from pipeline.models import EegSample, IngestionLog
from pipeline.schemas import IngestRequest, IngestResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database connection on startup and close on shutdown"""
    init_db()  # Ensure DB is initialized before handling requests
    yield


app = FastAPI(title="EEG Pipeline API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ingest_router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])
query_router = APIRouter(prefix="/api/eeg", tags=["Query"])


@ingest_router.post("/", response_model=IngestResponse)
def ingest_eeg_data(request: IngestRequest, db: Session = Depends(get_db)):
    """Endpoint to ingest EEG data chunks"""
    existing = (
        db.query(IngestionLog)
        .filter_by(
            recording_id=request.recording_id, chunk_start_sec=request.chunk_index
        )
        .first()
    )
    if existing:
        return IngestResponse(status="duplicate", message="Chunk already ingested")
    # expand chunk into individual samples and store in EegSample table
    sfreq = len(request.data[0])  # number of samples in the chunk
    samples = []
    for ch_idx, channel in enumerate(request.channels):
        for sample_idx, value in enumerate(request.data[ch_idx]):
            samples.append(
                EegSample(
                    patient_id=request.recording_id.split("_")[0],
                    recording_id=request.recording_id,
                    channel=channel,
                    timestamp_sec=request.chunk_index + sample_idx / sfreq,
                    value_uv=value,
                )
            )
    # Audit log
    check_sum = hashlib.sha256(json.dumps(request.data).encode()).hexdigest()
    log_entry = IngestionLog(
        patient_id=request.recording_id.split("_")[0],
        recording_id=request.recording_id,
        chunk_start_sec=request.chunk_index,
        chunk_end_sec=request.chunk_index + len(request.data[0]) / sfreq,
        num_samples=len(request.data[0]) * len(request.channels),
        checksum=check_sum,
    )
    db.add_all(samples + [log_entry])
    db.commit()

    return IngestResponse(status="success", message="Chunk ingested successfully")


@query_router.get("/{patient_id}/recordings")
def get_patient_recordings(patient_id: str, db: Session = Depends(get_db)):
    """Endpoint to get summary of EEG data for a patient"""
    total_samples = db.query(EegSample).filter_by(patient_id=patient_id).count()
    if total_samples == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    channels = (
        db.query(EegSample.channel).filter_by(patient_id=patient_id).distinct().all()
    )
    return {
        "patient_id": patient_id,
        "total_samples": total_samples,
        "channels": [ch[0] for ch in channels],
    }


@query_router.get("/{patient_id}/recordings/{recording_id}/summary")
def get_recording_summary(
    patient_id: str, recording_id: str, db: Session = Depends(get_db)
):
    """Endpoint to get summary of a specific recording"""
    total_samples = (
        db.query(EegSample)
        .filter_by(patient_id=patient_id, recording_id=recording_id)
        .count()
    )
    if total_samples == 0:
        raise HTTPException(status_code=404, detail="Recording not found")
    channels = (
        db.query(EegSample.channel)
        .filter_by(patient_id=patient_id, recording_id=recording_id)
        .distinct()
        .all()
    )
    return {
        "patient_id": patient_id,
        "recording_id": recording_id,
        "total_samples": total_samples,
        "channels": [ch[0] for ch in channels],
    }


@query_router.get("/{patient_id}/recordings/{recording_id}/data")
def get_recording_data(
    patient_id: str,
    recording_id: str,
    start_sec: float,
    end_sec: float,
    db: Session = Depends(get_db),
):
    """Endpoint to get EEG data for a specific recording within a time range"""
    samples = (
        db.query(EegSample)
        .filter_by(patient_id=patient_id, recording_id=recording_id)
        .filter(EegSample.timestamp_sec >= start_sec)
        .filter(EegSample.timestamp_sec < end_sec)
        .order_by(EegSample.timestamp_sec)
        .all()
    )
    return {
        "patient_id": patient_id,
        "recording_id": recording_id,
        "start_sec": start_sec,
        "end_sec": end_sec,
        "samples": [
            {
                "channel": s.channel,
                "timestamp_sec": s.timestamp_sec,
                "value_uv": s.value_uv,
            }
            for s in samples
        ],
    }


@app.get("/health", response_model=IngestResponse)
def health_check():
    """Health check endpoint to verify API is running"""
    return IngestResponse(status="healthy", message="API is up and running")


app.include_router(ingest_router)
app.include_router(query_router)
