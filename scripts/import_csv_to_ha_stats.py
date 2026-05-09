#!/usr/bin/env python3
"""
HeatPump Hero — import CSV into HA Long-Term Statistics.

Use case: HeatPump Hero installed mid-life. You have historical kWh data from
your old utility-meter export, Shelly cloud, vendor cloud, or a previous
HA install. This script backfills it via HA's `recorder.import_statistics`
websocket call so the long-term graphs and SCOP comparisons reach back
into pre-HeatPump Hero history.

Input CSV format (header row required):
    timestamp,state,sum
    2024-01-01T00:00:00+00:00,12345.67,12345.67
    2024-02-01T00:00:00+00:00,13456.78,13456.78
    ...

Columns:
    timestamp — ISO 8601 with timezone, must be on hour boundary
    state     — instantaneous value (e.g. kWh on the meter at that time)
    sum       — cumulative sum since recorder began (typically same as state
                for total_increasing sensors)

Usage:
    HA_BASE_URL=http://homeassistant.local:8123 \\
    HA_TOKEN=eyJhb... \\
    python3 import_csv_to_ha_stats.py \\
        --entity sensor.hph_thermal_energy_active \\
        --unit kWh \\
        --csv old_thermal_energy.csv

Notes:
    - Entity must already exist in HA (statistic_id matches the entity).
    - For a metered (cumulative) source: state == sum.
    - For a measurement source (e.g. live COP): state = mean over the hour,
      sum = N/A; use --source recorder and only state column.
    - Backups your DB first — this writes into long-term statistics.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.parse

try:
    import websocket  # pip install websocket-client
except ImportError:
    print("websocket-client not installed. Install:  pip install websocket-client", file=sys.stderr)
    sys.exit(1)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--entity", required=True, help="Statistic ID (entity_id of the target sensor)")
    p.add_argument("--unit", required=True, help="Unit of measurement (kWh, °C, ...)")
    p.add_argument("--csv", required=True, help="Path to CSV file (header: timestamp,state,sum)")
    p.add_argument("--name", default=None, help="Display name for the statistic (default: entity)")
    p.add_argument("--source", default="recorder", choices=["recorder"],
                   help="Statistic source — 'recorder' for HA-managed entities")
    args = p.parse_args()

    base_url = os.environ.get("HA_BASE_URL", "http://homeassistant.local:8123").rstrip("/")
    token = os.environ.get("HA_TOKEN")
    if not token:
        print("HA_TOKEN environment variable required", file=sys.stderr)
        return 1

    parsed = urllib.parse.urlparse(base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = f"{ws_scheme}://{parsed.netloc}/api/websocket"

    # Read CSV
    rows: list[dict] = []
    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            entry = {"start": r["timestamp"]}
            if "state" in r and r["state"]:
                entry["state"] = float(r["state"])
            if "sum" in r and r["sum"]:
                entry["sum"] = float(r["sum"])
            rows.append(entry)
    if not rows:
        print("CSV is empty", file=sys.stderr)
        return 1
    print(f"loaded {len(rows)} rows from {args.csv}")

    # Connect + auth
    ws = websocket.create_connection(ws_url, timeout=30)
    auth_required = json.loads(ws.recv())
    assert auth_required["type"] == "auth_required"
    ws.send(json.dumps({"type": "auth", "access_token": token}))
    auth_ok = json.loads(ws.recv())
    if auth_ok.get("type") != "auth_ok":
        print(f"auth failed: {auth_ok}", file=sys.stderr)
        return 1

    # Import
    msg = {
        "id": 1,
        "type": "recorder/import_statistics",
        "metadata": {
            "has_mean": False,
            "has_sum": True,
            "name": args.name or args.entity,
            "source": args.source,
            "statistic_id": args.entity,
            "unit_of_measurement": args.unit,
        },
        "stats": rows,
    }
    ws.send(json.dumps(msg))
    result = json.loads(ws.recv())
    ws.close()

    if result.get("success"):
        print(f"imported {len(rows)} statistics for {args.entity}")
        return 0
    else:
        print(f"import failed: {result}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
