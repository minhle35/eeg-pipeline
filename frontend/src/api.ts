import type { RecordingsResponse, SummaryResponse, DataResponse } from "./types";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchRecordings(patientId: string): Promise<RecordingsResponse> {
  const res = await fetch(`${BASE}/api/eeg/${patientId}/recordings`);
  if (!res.ok) throw new Error(`Failed to fetch recordings: ${res.status}`);
  return res.json();
}

export async function fetchSummary(patientId: string, recordingId: string): Promise<SummaryResponse> {
  const res = await fetch(`${BASE}/api/eeg/${patientId}/recordings/${recordingId}/summary`);
  if (!res.ok) throw new Error(`Failed to fetch summary: ${res.status}`);
  return res.json();
}

export async function fetchData(
  patientId: string,
  recordingId: string,
  startSec: number,
  endSec: number
): Promise<DataResponse> {
  const res = await fetch(
    `${BASE}/api/eeg/${patientId}/recordings/${recordingId}/data?start_sec=${startSec}&end_sec=${endSec}`
  );
  if (!res.ok) throw new Error(`Failed to fetch data: ${res.status}`);
  return res.json();
}
