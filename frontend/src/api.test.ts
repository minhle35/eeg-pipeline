import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchRecordings, fetchSummary, fetchData } from "./api";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

describe("fetchRecordings", () => {
  it("returns parsed response on success", async () => {
    const data = { patient_id: "chb01", total_samples: 100, channels: ["FP1-F7"] };
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(data) });

    const result = await fetchRecordings("chb01");
    expect(result).toEqual(data);
    expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining("/api/eeg/chb01/recordings"));
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404 });
    await expect(fetchRecordings("chb01")).rejects.toThrow("404");
  });
});

describe("fetchData", () => {
  it("builds correct URL with query params", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

    await fetchData("chb01", "chb01_03.edf", 0, 1);
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("start_sec=0");
    expect(url).toContain("end_sec=1");
    expect(url).toContain("chb01_03.edf");
  });
});
