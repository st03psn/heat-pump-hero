#!/usr/bin/env python3
"""
HeishaHub — export script.

Reads HA long-term statistics for HeishaHub entities and writes them
to CSV / JSON / XLSX. Invoked by `shell_command.heishahub_export` (see
the `heishahub_export.yaml` package).

Configuration via environment variables:
  HA_BASE_URL          e.g. http://homeassistant.local:8123
  HA_TOKEN             long-lived access token
  HEISHAHUB_TARGET     output directory (default: /config/heishahub_exports)
  HEISHAHUB_FORMAT     csv | json | xlsx (default: csv)
  HEISHAHUB_PERIOD     last_day | last_week | last_month | last_year | all_time

These are typically read from `input_text.heishahub_export_target_path`
etc. and passed in by the shell_command call.

Output: one file per entity, plus a combined summary file.
File naming: heishahub_<entity-id>_<period>_<YYYYMMDD-HHMMSS>.<ext>

Dependencies:
  - urllib (stdlib)
  - For xlsx: openpyxl (`pip install openpyxl`)
"""

from __future__ import annotations

import csv
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Entity list to export. Edit if you want fewer / more.
DEFAULT_ENTITIES = [
    "sensor.heishahub_thermal_energy_active",
    "sensor.heishahub_electrical_energy_active",
    "sensor.heishahub_thermal_daily",
    "sensor.heishahub_thermal_monthly",
    "sensor.heishahub_thermal_yearly",
    "sensor.heishahub_electrical_daily",
    "sensor.heishahub_electrical_monthly",
    "sensor.heishahub_electrical_yearly",
    "sensor.heishahub_cop_live",
    "sensor.heishahub_cop_daily",
    "sensor.heishahub_cop_monthly",
    "sensor.heishahub_scop",
    "sensor.heishahub_thermal_monthly_split_heating",
    "sensor.heishahub_thermal_monthly_split_dhw",
    "sensor.heishahub_thermal_monthly_split_cooling",
    "sensor.heishahub_electrical_monthly_split_heating",
    "sensor.heishahub_electrical_monthly_split_dhw",
    "sensor.heishahub_electrical_monthly_split_cooling",
    "sensor.heishahub_source_outdoor_temp",
    "sensor.heishahub_source_outlet_temp",
    "sensor.heishahub_source_inlet_temp",
    "sensor.heishahub_source_compressor_freq",
    "sensor.heishahub_source_pump_pressure",
]


def period_to_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    return {
        "last_day":   now - timedelta(days=1),
        "last_week":  now - timedelta(days=7),
        "last_month": now - timedelta(days=30),
        "last_year":  now - timedelta(days=365),
        "all_time":   datetime(2000, 1, 1, tzinfo=timezone.utc),
    }.get(period, now - timedelta(days=30))


def fetch_history(base_url: str, token: str, entity: str, start: datetime) -> list[dict]:
    """Fetch state history for an entity via the REST API."""
    url = f"{base_url}/api/history/period/{start.isoformat()}?filter_entity_id={entity}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data[0] if data else []


def write_csv(path: Path, entity: str, history: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "last_changed", "state", "unit_of_measurement"])
        for row in history:
            w.writerow([
                row.get("entity_id", entity),
                row.get("last_changed", ""),
                row.get("state", ""),
                row.get("attributes", {}).get("unit_of_measurement", ""),
            ])


def write_json(path: Path, entity: str, history: list[dict]) -> None:
    path.write_text(json.dumps(history, indent=2), encoding="utf-8")


def write_xlsx(path: Path, entity: str, history: list[dict]) -> None:
    try:
        from openpyxl import Workbook
    except ImportError:
        print(f"openpyxl not installed; falling back to CSV for {entity}", file=sys.stderr)
        write_csv(path.with_suffix(".csv"), entity, history)
        return
    wb = Workbook()
    ws = wb.active
    ws.title = entity[:30]
    ws.append(["entity_id", "last_changed", "state", "unit"])
    for row in history:
        ws.append([
            row.get("entity_id", entity),
            row.get("last_changed", ""),
            row.get("state", ""),
            row.get("attributes", {}).get("unit_of_measurement", ""),
        ])
    wb.save(path)


def main() -> int:
    base_url = os.environ.get("HA_BASE_URL", "http://homeassistant.local:8123").rstrip("/")
    token = os.environ.get("HA_TOKEN")
    if not token:
        print("HA_TOKEN environment variable required", file=sys.stderr)
        return 1

    target = Path(os.environ.get("HEISHAHUB_TARGET", "/config/heishahub_exports"))
    target.mkdir(parents=True, exist_ok=True)
    fmt = os.environ.get("HEISHAHUB_FORMAT", "csv").lower()
    period = os.environ.get("HEISHAHUB_PERIOD", "last_month")
    start = period_to_start(period)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    entities = os.environ.get("HEISHAHUB_ENTITIES", "").split(",")
    entities = [e.strip() for e in entities if e.strip()] or DEFAULT_ENTITIES

    written: list[Path] = []
    for entity in entities:
        try:
            hist = fetch_history(base_url, token, entity, start)
        except urllib.error.HTTPError as e:
            print(f"skip {entity}: HTTP {e.code}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"skip {entity}: {e}", file=sys.stderr)
            continue
        if not hist:
            continue

        safe_entity = entity.replace(".", "_")
        ext = "xlsx" if fmt == "xlsx" else fmt
        out = target / f"heishahub_{safe_entity}_{period}_{timestamp}.{ext}"

        if fmt == "json":
            write_json(out, entity, hist)
        elif fmt == "xlsx":
            write_xlsx(out, entity, hist)
        else:
            write_csv(out, entity, hist)
        written.append(out)
        print(f"wrote {out} ({len(hist)} rows)")

    print(f"\nExport complete: {len(written)} files in {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
