"""Tests for EEG Pipeline API endpoints."""

SAMPLE_CHUNK = {
    "recording_id": "chb01_03.edf",
    "chunk_index": 0,
    "channels": ["FP1-F7", "F7-T7"],
    "data": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],  # 2 channels × 3 samples
    "timestamp": 1708300000.0,
}


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_ingest_chunk(client):
    res = client.post("/api/ingest/", json=SAMPLE_CHUNK)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"


def test_ingest_duplicate(client):
    client.post("/api/ingest/", json=SAMPLE_CHUNK)
    res = client.post("/api/ingest/", json=SAMPLE_CHUNK)
    assert res.status_code == 200
    assert res.json()["status"] == "duplicate"


def test_get_recordings(client):
    client.post("/api/ingest/", json=SAMPLE_CHUNK)
    res = client.get("/api/eeg/chb01/recordings")
    assert res.status_code == 200
    body = res.json()
    assert body["patient_id"] == "chb01"
    assert body["total_samples"] == 6  # 2 channels × 3 samples
    assert set(body["channels"]) == {"FP1-F7", "F7-T7"}


def test_get_recordings_not_found(client):
    res = client.get("/api/eeg/unknown/recordings")
    assert res.status_code == 404


def test_get_recording_summary(client):
    client.post("/api/ingest/", json=SAMPLE_CHUNK)
    res = client.get("/api/eeg/chb01/recordings/chb01_03.edf/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["recording_id"] == "chb01_03.edf"
    assert body["total_samples"] == 6
    assert set(body["channels"]) == {"FP1-F7", "F7-T7"}


def test_get_recording_data(client):
    client.post("/api/ingest/", json=SAMPLE_CHUNK)
    res = client.get("/api/eeg/chb01/recordings/chb01_03.edf/data?start_sec=0&end_sec=1")
    assert res.status_code == 200
    body = res.json()
    assert len(body["samples"]) == 6
    assert body["samples"][0]["channel"] in ("FP1-F7", "F7-T7")


def test_get_recording_data_empty_range(client):
    client.post("/api/ingest/", json=SAMPLE_CHUNK)
    res = client.get("/api/eeg/chb01/recordings/chb01_03.edf/data?start_sec=99&end_sec=100")
    assert res.status_code == 200
    assert res.json()["samples"] == []


def test_ingest_validation_error(client):
    res = client.post("/api/ingest/", json={"recording_id": "test"})
    assert res.status_code == 422
