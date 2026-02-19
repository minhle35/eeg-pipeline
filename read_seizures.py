#!/usr/bin/env python3
"""
Analyze CHB-MIT EEG files (.edf) and seizure annotations from summary files.
"""

import re
import mne
from pathlib import Path
import sys


def parse_summary(summary_file):
    """Parse a patient summary file. Returns dict mapping filename -> list of seizures."""
    seizure_map = {}

    with open(summary_file, "r") as f:
        content = f.read()

    blocks = re.split(r"(?=File Name:)", content)
    for block in blocks:
        name_match = re.search(r"File Name:\s*(\S+)", block)
        if not name_match:
            continue

        filename = name_match.group(1)
        seizures = []

        starts = re.findall(r"Seizure\s*\d*\s*Start Time:\s*(\d+)", block)
        ends = re.findall(r"Seizure\s*\d*\s*End Time:\s*(\d+)", block)

        for s, e in zip(starts, ends):
            start, end = int(s), int(e)
            seizures.append({"start": start, "end": end, "duration": end - start})

        seizure_map[filename] = seizures

    return seizure_map


def analyze_edf_file(edf_file, seizures):
    """Analyze EEG file and print summary"""

    try:
        raw = mne.io.read_raw_edf(str(edf_file), preload=False, verbose=False)

        duration_sec = raw.times[-1]
        duration_hours = duration_sec / 3600
        sfreq = int(raw.info["sfreq"])
        num_channels = len(raw.ch_names)

        print(f"\n{'=' * 70}")
        print(f"File: {Path(edf_file).name}")
        print(f"{'=' * 70}")
        print(
            f"Duration:        {duration_hours:.2f} hours ({duration_sec:.0f} seconds)"
        )
        print(f"Sampling rate:   {sfreq} Hz")
        print(f"Channels:        {num_channels}")
        print(f"Channel names:   {', '.join(raw.ch_names[:3])}... (showing first 3)")
        print(f"Seizures:        {len(seizures)}")

        if seizures:
            print("\nSeizure Details:")
            for i, sz in enumerate(seizures, 1):
                print(
                    f"  Seizure {i}: {sz['start']:5d}-{sz['end']:5d} sec "
                    f"({sz['duration']:3d} sec = {sz['duration'] / 60:.1f} min)"
                )

        print(f"{'=' * 70}\n")

        return {
            "file": Path(edf_file).name,
            "duration_sec": duration_sec,
            "sfreq": sfreq,
            "channels": num_channels,
            "seizures": len(seizures),
        }

    except Exception as e:
        print(f"Error analyzing {edf_file}: {e}")
        return None


def analyze_patient(patient_dir, patient_id="chb01", limit=None):
    """Analyze all files for a patient"""

    patient_path = Path(patient_dir)

    if not patient_path.exists():
        print(f"Error: Patient directory not found: {patient_path}")
        return

    # Parse summary file for seizure info
    summary_file = patient_path / f"{patient_id}-summary.txt"
    if not summary_file.exists():
        print(f"Error: Summary file not found: {summary_file}")
        return

    seizure_map = parse_summary(summary_file)

    # Get all EDF files
    edf_files = sorted(patient_path.glob(f"{patient_id}_*.edf"))

    if limit:
        edf_files = edf_files[:limit]

    print(f"\n{'#' * 70}")
    print(f"# Analyzing Patient: {patient_id}")
    print(
        f"# Found {len(edf_files)} files ({sum(1 for s in seizure_map.values() if s)} with seizures)"
    )
    print(f"{'#' * 70}")

    total_seizures = 0
    total_duration = 0

    for edf_file in edf_files:
        seizures = seizure_map.get(edf_file.name, [])
        has_sz = f"{len(seizures)} seizure(s)" if seizures else "no seizures"
        print(f"Processing: {edf_file.name} ({has_sz})")
        result = analyze_edf_file(edf_file, seizures)

        if result:
            total_duration += result["duration_sec"]
            total_seizures += result["seizures"]

    # Summary
    print(f"\n{'#' * 50}")
    print(f"# SUMMARY for {patient_id}")
    print(f"{'#' * 50}")
    print(f"Total files:     {len(edf_files)}")
    print(f"Total duration:  {total_duration / 3600:.1f} hours")
    print(f"Total seizures:  {total_seizures}")
    if total_duration > 0:
        print(f"Seizures/24h:    {(total_seizures / (total_duration / 3600) * 24):.1f}")
    print(f"{'#' * 50}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = "chb-mit/physionet.org/files/chbmit/1.0.0/chb01"

    if len(sys.argv) > 2:
        patient_id = sys.argv[2]
    else:
        patient_id = "chb01"

    if len(sys.argv) > 3:
        limit = int(sys.argv[3])
    else:
        limit = None

    # Run analysis
    analyze_patient(data_dir, patient_id, limit)
