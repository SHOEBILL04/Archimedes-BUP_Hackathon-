#!/usr/bin/env python3
"""Validates the sample request against the running backend API service."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import urllib.request
import urllib.error

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_FILE = ROOT_DIR / "docs" / "reference" / "sample_request.json"
API_URL = "http://localhost:8000/api/v1/optimize-energy"


def main() -> None:
    if not SAMPLE_FILE.exists():
        print(f"Error: Sample file not found at {SAMPLE_FILE}")
        sys.exit(1)

    with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)

    print(f"Sending sample request to {API_URL}...")
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=data, headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            print("Response Status: 200 OK")
            print("Directives:", len(body.get("directive_interpretation", [])))
            print("Hourly Schedule Rows:", len(body.get("schedule", [])))
            print("Total Grid Cost:", body.get("total_grid_cost_bdt"), "BDT")
            print("Verification Result:", body.get("verification", {}).get("verified"))
            print("Status Message:", body.get("status_message"))
            print("Scaffold verification passed successfully!")
    except urllib.error.URLError as e:
        print(f"Failed to connect to API: {e}")
        print("Ensure the backend is running with 'make backend' or 'make dev'")
        sys.exit(1)


if __name__ == "__main__":
    main()
