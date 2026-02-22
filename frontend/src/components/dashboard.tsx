import { useEffect, useState } from "react";
import { fetchRecordings, fetchSummary, fetchData } from "../api";
import type { RecordingsResponse, SummaryResponse, DataResponse } from "../types";

const PATIENT_ID = "chb01";
const RECORDING_ID = "chb01_03.edf";
const MAX_SAMPLES = 43;

export default function Dashboard() {
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [recordings, setRecordings] = useState<RecordingsResponse | null>(null);
  const [detail, setDetail] = useState<{ summary: SummaryResponse; data: DataResponse } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/health")
      .then((r) => r.ok && setHealthy(true))
      .catch(() => setHealthy(false));

    fetchRecordings(PATIENT_ID)
      .then(setRecordings)
      .catch((e) => setError(e.message));
  }, []);

  async function handleView() {
    try {
      const [summary, data] = await Promise.all([
        fetchSummary(PATIENT_ID, RECORDING_ID),
        fetchData(PATIENT_ID, RECORDING_ID, 0, 1),
      ]);
      setDetail({ summary, data });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  }

  return (
    <div className="dashboard">
      <header className="header">
        <h1>EEG Pipeline Dashboard</h1>
        <span className={`status ${healthy === true ? "ok" : healthy === false ? "err" : ""}`}>
          {healthy === true ? "● API Connected" : healthy === false ? "● Disconnected" : "● Checking..."}
        </span>
      </header>

      {error && <p className="error">{error}</p>}

      <section>
        <h2>Patient: {PATIENT_ID}</h2>
        {recordings ? (
          <>
            <table>
              <thead>
                <tr>
                  <th>Total Samples</th>
                  <th>Channels</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{recordings.total_samples.toLocaleString()}</td>
                  <td>{recordings.channels.length}</td>
                </tr>
              </tbody>
            </table>
            <div style={{ marginTop: "0.5rem" }}>
              {recordings.channels.map((ch) => (
                <code key={ch} className="channel-tag">{ch}</code>
              ))}
            </div>
            <button onClick={handleView} style={{ marginTop: "1rem" }}>
              View {RECORDING_ID}
            </button>
          </>
        ) : (
          <p>Loading recordings...</p>
        )}
      </section>

      {detail && (
        <section className="detail">
          <h2>Recording: {detail.summary.recording_id}</h2>
          <p>
            <strong>Channels:</strong> {detail.summary.channels.join(", ")} &nbsp;|&nbsp;
            <strong>Total samples:</strong> {detail.summary.total_samples.toLocaleString()}
          </p>

          <h3>Samples (0–1s)</h3>
          {detail.data.samples.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Channel</th>
                  <th>Time (s)</th>
                  <th>Value (µV)</th>
                </tr>
              </thead>
              <tbody>
                {detail.data.samples.map((s, i) => (
                  <tr key={i}>
                    <td>{s.channel}</td>
                    <td>{s.timestamp_sec.toFixed(3)}</td>
                    <td>{s.value_uv.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No samples in this range.</p>
          )}
        </section>
      )}
    </div>
  );
}
