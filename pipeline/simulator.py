# EEG device simulator
"""
This module simulates an EEG device by using real data from CHB-MIT Scalp EEG Database
- iteratively read EDF file
- slice it into 1-second segments/windows
- yield each segment to an API for real-time processing

The simulator can be used for testing and development of real-time EEG processing algorithms without needing a physical EEG device.

An EDF file for `chb01_01.edf` has:
- 23 channels (EEG electrodes)
- Sampling rate: 256 Hz
- Duration: 1 hour (3600 seconds)
- a 1-hour recording at 256 Hz means 256 * 23 channels = 5888 values per second, and 3600 seconds means 3600 * 5888 = 21,196,800 total data points in the file.
"""

import mne
import numpy as np
import httpx
import time
from pathlib import Path


def load_edf_file(edf_file):
    """Load EDF file and return raw data object"""
    raw = mne.io.read_raw_edf(str(edf_file), preload=True, verbose=False)
    return raw.ch_names, raw.get_data(), int(raw.info["sfreq"])


def make_chunk(channels, data, sfreq) -> list:
    """split full recording into 1-second chunks
    This process is similar to how network packets are split into smaller pieces for transmission. Each chunk will contain data for all channels but only for a 1-second window.
    """
    chunks = []
    chunk_size = int(sfreq)
    num_samples = data.shape[1]
    for start in range(0, num_samples, chunk_size):
        end = start + chunk_size
        if end > num_samples:
            break  # skip last chunk if it's less than 1 second
        # each chunk is a 2D array of shape (channels x samples_in_chunk), where samples_in_chunk = sfreq (number of samples in 1 second)
        chunk = data[:, start:end]
        chunks.append(chunk)
    return chunks


def stream_chunks_to_api(
    channels,
    chunks,
    recording_id: str,
    api_url: str = "http://localhost:8000/api/ingest/",
    limit: int | None = None,
    delay: float = 0.01,
):
    """Send chunks to API endpoint simulating real-time streaming"""
    chunks_to_send = chunks[:limit] if limit else chunks
    total = len(chunks_to_send)

    with httpx.Client(timeout=30.0) as client:
        for i, chunk in enumerate(chunks_to_send):
            payload = {
                "channels": channels,
                "timestamp": time.time(),
                "chunk_index": i,
                "recording_id": recording_id,
                "data": chunk.tolist(),
            }
            try:
                response = client.post(api_url, json=payload)
                response.raise_for_status()
                if (i + 1) % 10 == 0 or i == 0:
                    print(f"  Sent {i + 1}/{total} chunks for {recording_id}")
            except httpx.HTTPError as e:
                print(f"Error sending chunk {i}: {e}")
                break
            time.sleep(delay)


if __name__ == "__main__":
    edf_file = "chb-mit/physionet.org/files/chbmit/1.0.0/chb01/chb01_01.edf"
    raw_ch_names, raw_data, raw_sfreq = load_edf_file(edf_file)
    chunks = make_chunk(raw_ch_names, raw_data, raw_sfreq)
    recording_id = Path(edf_file).name

    # Limit to 10 chunks for quick testing (remove limit for full ingestion)
    limit = 10
    print(f"Total chunks available: {len(chunks)}")
    print(f"Sending {limit} chunks for testing...")
    print(f"Chunk shape: {chunks[0].shape} (channels x samples)")

    stream_chunks_to_api(raw_ch_names, chunks, recording_id, limit=limit)
    print("Done!")
