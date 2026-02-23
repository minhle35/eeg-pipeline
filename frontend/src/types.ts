export interface RecordingsResponse {
  patient_id: string;
  total_samples: number;
  channels: string[];
}

export interface SummaryResponse {
  patient_id: string;
  recording_id: string;
  total_samples: number;
  channels: string[];
}

export interface Sample {
  channel: string;
  timestamp_sec: number;
  value_uv: number;
}

export interface DataResponse {
  patient_id: string;
  recording_id: string;
  start_sec: number;
  end_sec: number;
  samples: Sample[];
}
