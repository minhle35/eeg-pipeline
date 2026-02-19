from pydantic import BaseModel


class IngestRequest(BaseModel):
    """Request model for ingesting EEG data"""

    recording_id: str
    chunk_index: int
    channels: list[str]
    data: list[list[float]]  # 2D list: channels x samples
    timestamp: float


class IngestResponse(BaseModel):
    """Response model for ingesting EEG data"""

    status: str
    message: str
