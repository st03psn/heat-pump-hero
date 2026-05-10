#!/usr/bin/env python3
"""HeatPump Hero -- backfill historical statistics from Shelly 3EM and Sensostar WMZ.

Reads monthly energy totals from the physical meter state-column in the HA SQLite
database (read-only), then imports them into the HPH utility_meter statistics via
HA's WebSocket recorder/import_statistics API.

What gets imported
------------------
  sensor.hph_thermal_monthly   -- calendar-month totals (Sensostar, from Nov 2025)
  sensor.hph_electrical_monthly -- calendar-month totals (Shelly, from Sep 2025)
  sensor.hph_thermal_yearly    -- heating-season Jul-Jun accumulator (Sensostar)
  sensor.hph_electrical_yearly -- heating-season Jul-Jun accumulator (Shelly)

The HA-level LTS sum-reset that happened 2026-01-28 -> 2026-02-13 (HA offline,
not a physical meter reset) is corrected via linear interpolation of the state
column at each month boundary.

Safety
------
Run without --confirm first: the script prints a dry-run table showing what
would be imported. Add --confirm to actually write to HA.

Usage
-----
  # Dry-run (default):
  HA_TOKEN=eyJh... python scripts/backfill_from_external_meters.py

  # Live import:
  HA_TOKEN=eyJh... python scripts/backfill_from_external_meters.py --confirm

  # Non-default paths / URLs:
  HA_DB=P:/home-assistant_v2.db HA_BASE_URL=http://192.168.111.73:8123 \
    HA_TOKEN=eyJh... python scripts/backfill_from_external_meters.py --confirm

Dependencies
------------
  pip install websocket-client
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import websocket
except ImportError:
    print("websocket-client not installed.  pip install websocket-client", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HA_DB = os.environ.get("HA_DB", r"P:\home-assistant_v2.db")
HA_BASE = os.environ.get("HA_BASE_URL", "http://192.168.111.73:8123").rstrip("/")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

SHELLY_ENTITY = "sensor.3em_wpaussen_total_active_energy"
SENSOSTAR_ENTITY = "sensor.sensostar_9ce898_sensostar_energy"

# HPH target entities (utility_meter cycle=monthly / cron Jul 1 yearly)
HPH_THERMAL_MONTHLY = "sensor.hph_thermal_monthly"
HPH_ELECTRICAL_MONTHLY = "sensor.hph_electrical_monthly"
HPH_THERMAL_YEARLY = "sensor.hph_thermal_yearly"
HPH_ELECTRICAL_YEARLY = "sensor.hph_electrical_yearly"

# Heating season start (matching cron "0 0 1 7 *")
SEASON_START = datetime(2025, 7, 1, 0, 0, 0)  # local CET/CEST

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _open_db() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{HA_DB}?mode=ro", uri=True)


def _meta_id(con: sqlite3.Connection, stat_id: str) -> int | None:
    cur = con.execute("SELECT id FROM statistics_meta WHERE statistic_id=?", (stat_id,))
    row = cur.fetchone()
    return row[0] if row else None


def _state_at(con: sqlite3.Connection, meta_id: int, ts: datetime) -> float | None:
    """Physical meter reading at `ts`, linearly interpolated from nearest LTS rows."""
    ts_epoch = int(ts.replace(tzinfo=timezone.utc).timestamp())

    cur = con.execute(
        "SELECT start_ts, state FROM statistics "
        "WHERE metadata_id=? AND state IS NOT NULL AND start_ts <= ? "
        "ORDER BY start_ts DESC LIMIT 1",
        (meta_id, ts_epoch),
    )
    before = cur.fetchone()

    cur = con.execute(
        "SELECT start_ts, state FROM statistics "
        "WHERE metadata_id=? AND state IS NOT NULL AND start_ts > ? "
        "ORDER BY start_ts ASC LIMIT 1",
        (meta_id, ts_epoch),
    )
    after = cur.fetchone()

    if before and not after:
        return before[1]
    if after and not before:
        return after[1]
    if not before and not after:
        return None

    ts_b, v_b = before
    ts_a, v_a = after
    if ts_a == ts_b:
        return float(v_b)
    frac = (ts_epoch - ts_b) / (ts_a - ts_b)
    return float(v_b) + frac * (float(v_a) - float(v_b))


def _cet_offset(month: int) -> int:
    """UTC offset in hours for Germany: CEST(+2) Apr-Oct, CET(+1) Nov-Mar."""
    return 2 if 4 <= month <= 10 else 1


def _month_start_utc(year: int, month: int) -> datetime:
    """First instant of a calendar month in local time, expressed as UTC datetime."""
    offset_h = _cet_offset(month)
    local_midnight = datetime(year, month, 1, 0, 0, 0)
    return local_midnight - timedelta(hours=offset_h)


def _month_end_utc(year: int, month: int) -> datetime:
    """Last full hour of a calendar month (= start of next month) in UTC."""
    if month == 12:
        return _month_start_utc(year + 1, 1)
    return _month_start_utc(year, month + 1)


# ---------------------------------------------------------------------------
# Monthly delta computation
# ---------------------------------------------------------------------------

MONTHS = [
    (2025, 9), (2025, 10), (2025, 11), (2025, 12),
    (2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5),
]


def compute_monthly_totals() -> dict[tuple[int, int], dict[str, float | None]]:
    """Return {(year, month): {"thermal": kWh|None, "electrical": kWh}} using
    physical meter state column with gap interpolation at month boundaries."""
    con = _open_db()
    sh_id = _meta_id(con, SHELLY_ENTITY)
    se_id = _meta_id(con, SENSOSTAR_ENTITY)

    result: dict[tuple[int, int], dict[str, float | None]] = {}

    for yr, mo in MONTHS:
        ts_start = _month_start_utc(yr, mo)
        ts_end = _month_end_utc(yr, mo)
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)
        if ts_end > now_utc:
            ts_end = now_utc  # partial month

        sh_start = _state_at(con, sh_id, ts_start) if sh_id else None
        sh_end = _state_at(con, sh_id, ts_end) if sh_id else None
        se_start = _state_at(con, se_id, ts_start) if se_id else None
        se_end = _state_at(con, se_id, ts_end) if se_id else None

        el = round(sh_end - sh_start, 2) if (sh_start is not None and sh_end is not None) else None
        th = round(se_end - se_start, 1) if (se_start is not None and se_end is not None) else None

        result[(yr, mo)] = {"thermal": th, "electrical": el}

    con.close()
    return result


# ---------------------------------------------------------------------------
# Statistics entry builders
# ---------------------------------------------------------------------------

def _iso(dt_utc: datetime) -> str:
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def build_monthly_stats(
    totals: dict[tuple[int, int], dict[str, float | None]],
    channel: str,  # "thermal" | "electrical"
) -> list[dict]:
    """Build statistics entries for sensor.hph_{channel}_monthly.

    Each month contributes:
      - entry at month-start:  state=0,     sum=prev_cumulative, last_reset=month-start
      - entry at month-end-1h: state=total, sum=cumulative,       last_reset=month-start
    """
    stats: list[dict] = []
    cumulative = 0.0

    for yr, mo in MONTHS:
        val = totals.get((yr, mo), {}).get(channel)
        if val is None:
            continue  # no data for this month/channel -- skip

        ts_start = _month_start_utc(yr, mo)
        ts_end = _month_end_utc(yr, mo) - timedelta(hours=1)

        # Start of month: state resets to 0, cumulative sum continues
        stats.append({
            "start": _iso(ts_start),
            "state": 0.0,
            "sum": cumulative,
            "last_reset": _iso(ts_start),
        })
        cumulative += val
        # End of month: state = total accumulated, sum = cumulative
        stats.append({
            "start": _iso(ts_end),
            "state": round(val, 3),
            "sum": round(cumulative, 3),
            "last_reset": _iso(ts_start),
        })

    return stats


def build_yearly_stats(
    totals: dict[tuple[int, int], dict[str, float | None]],
    channel: str,
) -> list[dict]:
    """Build statistics entries for sensor.hph_{channel}_yearly.

    The heating season starts Jul 1 (cron "0 0 1 7 *").
    We provide one entry at each month-end showing the running accumulator.
    """
    season_start_utc = SEASON_START - timedelta(hours=_cet_offset(7))  # Jul = CEST
    last_reset_iso = _iso(season_start_utc)

    stats: list[dict] = []
    accumulated = 0.0

    for yr, mo in MONTHS:
        val = totals.get((yr, mo), {}).get(channel)
        if val is None:
            continue

        accumulated += val
        ts_end = _month_end_utc(yr, mo) - timedelta(hours=1)
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)
        if ts_end > now_utc:
            ts_end = now_utc

        stats.append({
            "start": _iso(ts_end),
            "state": round(accumulated, 3),
            "sum": round(accumulated, 3),
            "last_reset": last_reset_iso,
        })

    return stats


# ---------------------------------------------------------------------------
# WebSocket import
# ---------------------------------------------------------------------------

def ws_import(entity_id: str, stats: list[dict], unit: str = "kWh") -> bool:
    import urllib.parse

    parsed = urllib.parse.urlparse(HA_BASE)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = f"{ws_scheme}://{parsed.netloc}/api/websocket"

    ws = websocket.create_connection(ws_url, timeout=30)
    auth_required = json.loads(ws.recv())
    assert auth_required["type"] == "auth_required", auth_required

    ws.send(json.dumps({"type": "auth", "access_token": HA_TOKEN}))
    auth_ok = json.loads(ws.recv())
    if auth_ok.get("type") != "auth_ok":
        print(f"  auth failed: {auth_ok}", file=sys.stderr)
        ws.close()
        return False

    msg = {
        "id": 1,
        "type": "recorder/import_statistics",
        "metadata": {
            "has_mean": False,
            "has_sum": True,
            "name": entity_id,
            "source": "recorder",
            "statistic_id": entity_id,
            "unit_of_measurement": unit,
        },
        "stats": stats,
    }
    ws.send(json.dumps(msg))
    result = json.loads(ws.recv())
    ws.close()

    if result.get("success"):
        return True
    print(f"  import failed: {result}", file=sys.stderr)
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill HPH LTS from Shelly+Sensostar DB")
    ap.add_argument("--confirm", action="store_true",
                    help="Actually write to HA (default: dry-run preview only)")
    args = ap.parse_args()

    if args.confirm and not HA_TOKEN:
        print("ERROR: HA_TOKEN required for --confirm mode", file=sys.stderr)
        return 1

    print(f"\nHPH Backfill -- {'LIVE IMPORT' if args.confirm else 'DRY RUN (add --confirm to write)'}")
    print(f"DB: {HA_DB}")
    print(f"HA: {HA_BASE}\n")

    totals = compute_monthly_totals()

    # Print monthly table
    print(f"{'Month':<10} {'Thermal':>10} {'Electrical':>12} {'COP':>6}")
    print("-" * 44)
    th_total = el_total = 0.0
    for yr, mo in MONTHS:
        t = totals[(yr, mo)]
        th = t["thermal"]
        el = t["electrical"]
        th_str = f"{th:10.0f}" if th is not None else "       n/a"
        el_str = f"{el:10.1f}" if el is not None else "       n/a"
        cop_str = f"{th/el:6.2f}" if (th and el and el > 0) else "   n/a"
        partial = ""
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        end = _month_end_utc(yr, mo)
        if end > now_utc:
            partial = " (partial)"
        print(f"{yr}-{mo:02d}    {th_str}  {el_str}  {cop_str}{partial}")
        if th: th_total += th
        if el: el_total += el
    print("-" * 44)
    scop = th_total / el_total if el_total > 0 else 0
    print(f"{'TOTAL':<10}  {th_total:10.0f}  {el_total:10.1f}  {scop:6.2f}  (SCOP Nov->today)\n")

    # Build all 4 stat sets
    targets = [
        (HPH_THERMAL_MONTHLY,   build_monthly_stats(totals, "thermal"),   "monthly"),
        (HPH_ELECTRICAL_MONTHLY, build_monthly_stats(totals, "electrical"), "monthly"),
        (HPH_THERMAL_YEARLY,    build_yearly_stats(totals,  "thermal"),   "yearly"),
        (HPH_ELECTRICAL_YEARLY,  build_yearly_stats(totals,  "electrical"), "yearly"),
    ]

    for entity_id, stats, meter_type in targets:
        print(f"  {entity_id}  ({meter_type})  --> {len(stats)} entries")
        if args.confirm:
            ok = ws_import(entity_id, stats)
            print(f"    {'OK' if ok else 'FAILED'}")
        else:
            # Show first and last entry
            if stats:
                print(f"    first: {stats[0]}")
                print(f"    last:  {stats[-1]}")

    if not args.confirm:
        print("\nDry-run complete. Run with --confirm to write to HA.")
    else:
        print("\nImport complete. Reload the HPH integration or restart HA.")
        print("The SCOP trend chart and monthly COP comparisons now have historical data.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
