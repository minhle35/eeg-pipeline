import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Dashboard from "./dashboard";

// Mock the API module
vi.mock("../api", () => ({
  fetchRecordings: vi.fn(),
  fetchSummary: vi.fn(),
  fetchData: vi.fn(),
}));

import { fetchRecordings, fetchSummary, fetchData } from "../api";

const mockFetchRecordings = vi.mocked(fetchRecordings);
const mockFetchSummary = vi.mocked(fetchSummary);
const mockFetchData = vi.mocked(fetchData);

// Mock the /health fetch
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  vi.clearAllMocks();
  mockFetch.mockResolvedValue({ ok: true });
});

describe("Dashboard", () => {
  it("shows loading state initially", () => {
    mockFetchRecordings.mockReturnValue(new Promise(() => {})); // never resolves
    render(<Dashboard />);
    expect(screen.getByText("Loading recordings...")).toBeInTheDocument();
  });

  it("renders recordings after fetch", async () => {
    mockFetchRecordings.mockResolvedValue({
      patient_id: "chb01",
      total_samples: 5888,
      channels: ["FP1-F7", "F7-T7"],
    });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText("5,888")).toBeInTheDocument();
    });
    expect(screen.getByText("FP1-F7")).toBeInTheDocument();
    expect(screen.getByText("F7-T7")).toBeInTheDocument();
  });

  it("shows error on API failure", async () => {
    mockFetchRecordings.mockRejectedValue(new Error("Network error"));

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("fetches detail when View is clicked", async () => {
    mockFetchRecordings.mockResolvedValue({
      patient_id: "chb01",
      total_samples: 100,
      channels: ["FP1-F7"],
    });
    mockFetchSummary.mockResolvedValue({
      patient_id: "chb01",
      recording_id: "chb01_01.edf",
      total_samples: 50,
      channels: ["FP1-F7"],
    });
    mockFetchData.mockResolvedValue({
      patient_id: "chb01",
      recording_id: "chb01_01.edf",
      start_sec: 0,
      end_sec: 1,
      samples: [{ channel: "FP1-F7", timestamp_sec: 0.0, value_uv: 1.23 }],
    });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText("View")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("View"));

    await waitFor(() => {
      expect(screen.getByText("Recording: chb01_01.edf")).toBeInTheDocument();
    });
    expect(screen.getByText("1.23")).toBeInTheDocument();
  });
});
