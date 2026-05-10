#!/usr/bin/env python3
"""HeatPump Hero -- backfill historical statistics from Shelly 3EM and Sensostar WMZ.

Reads energy data from the physical meter state-column in the HA SQLite database
(read-only), then imports it into HPH statistics via HA's WebSocket
recorder/import_statistics API.

What gets imported
------------------
Default (monthly resolution):
  sensor.hph_thermal_monthly    -- calendar-month totals (Sensostar, from Nov 2025)
  sensor.hph_electrical_monthly -- calendar-month totals (Shelly, from Sep 2025)
  sensor.hph_thermal_yearly     -- heating-season Jul-Jun accumulator (Sensostar)
  sensor.hph_electrical_yearly  -- heating-season Jul-Jun accumulator (Shelly)

With --full (adds daily + hourly resolution):
  sensor.hph_thermal_daily      -- daily totals (fills 30-day bar charts)
  sensor.hph_electrical_daily   -- daily totals
  sensor.hph_cop_daily          -- daily COP (fills COP trend chart)
  sensor.hph_thermal_energy_active    -- hourly cumulative (fills statistics-graph)
  sensor.hph_electrical_energy_active -- hourly cumulative

The HA-level LTS sum-reset (2026-01-28 to 2026-02-13, HA offline, not a physical
meter reset) is corrected via linear interpolation of the state column at each
boundary.

Pre-HA reconstruction
---------------------
Both Shelly and Sensostar were commissioned at 0 kWh in Sep 2025. The Sensostar
only appeared in HA on Nov 10, 2025 at 2891 kWh. Shelly has been tracked since
Sep 25. Implied average COP (2891 / 476.23 = 6.07) is used to back-interpolate
thermal values for Sep, Oct and Nov 1-9.

Safety
------
Run without --confirm first: the script prints a dry-run table. Add --confirm to
actually write to HA.

Usage
-----
  # Dry-run monthly (default):
  HA_TOKEN=eyJh... python scripts/backfill_from_external_meters.py

  # Live import monthly:
  HA_TOKEN=eyJh... python scripts/backfill_from_external_meters.py --confirm

  # Full import (monthly + daily + hourly), dry-run:
  HA_TOKEN=eyJh... python scripts/backfill_from_external_meters.py --full

  # Full import, live:
  HA_TOKEN=eyJh... python scripts/backfill_from_external_meters.py --full --confirm

  # Non-default paths / URLs:
  HA_DB=P:/home-assistant_v2.db HA_BASE_URL=http://192.168.111.73:8123 \\
    HA_TOKEN=eyJh... python scripts/backfill_from_external_meters.py --full --confirm

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
from datetime import date, datetime, timedelta, timezone

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

# HPH target entities — monthly / yearly (utility_meter)
HPH_THERMAL_MONTHLY    = "sensor.hph_thermal_monthly"
HPH_ELECTRICAL_MONTHLY = "sensor.hph_electrical_monthly"
HPH_THERMAL_YEARLY     = "sensor.hph_thermal_yearly"
HPH_ELECTRICAL_YEARLY  = "sensor.hph_electrical_yearly"

# HPH target entities — daily (utility_meter cycle=daily)
HPH_THERMAL_DAILY    = "sensor.hph_thermal_daily"
HPH_ELECTRICAL_DAILY = "sensor.hph_electrical_daily"
HPH_COP_DAILY        = "sensor.hph_cop_daily"

# HPH target entities — cumulative energy (total_increasing, feeds utility_meters)
HPH_THERMAL_ENERGY_ACTIVE    = "sensor.hph_thermal_energy_active"
HPH_ELECTRICAL_ENERGY_ACTIVE = "sensor.hph_electrical_energy_active"

# HPH COP/SCOP LTS targets (mean-only, for charts)
HPH_COP_MONTHLY = "sensor.hph_cop_monthly"
HPH_SCOP        = "sensor.hph_scop"

# Heating season start (matching cron "0 0 1 7 *")
SEASON_START = datetime(2025, 7, 1, 0, 0, 0)  # local CET/CEST

# First Sensostar LTS row (verified from DB)
TS_SENSOSTAR_FIRST = datetime(2025, 11, 10, 13, 0, 0)  # UTC

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
        return float(before[1])
    if after and not before:
        return float(after[1])
    if not before and not after:
        return None

    ts_b, v_b = before
    ts_a, v_a = after
    if ts_a == ts_b:
        return float(v_b)
    frac = (ts_epoch - ts_b) / (ts_a - ts_b)
    return float(v_b) + frac * (float(v_a) - float(v_b))


def _load_all_rows(con: sqlite3.Connection, meta_id: int, ts_from: datetime) -> list[tuple[int, float]]:
    """Load all LTS rows from ts_from onward as (start_ts_epoch, state)."""
    t_from = int(ts_from.replace(tzinfo=timezone.utc).timestamp())
    cur = con.execute(
        "SELECT start_ts, state FROM statistics "
        "WHERE metadata_id=? AND state IS NOT NULL AND start_ts >= ? "
        "ORDER BY start_ts",
        (meta_id, t_from),
    )
    return [(int(r[0]), float(r[1])) for r in cur.fetchall()]


def _cet_offset(month: int) -> int:
    """UTC offset in hours for Germany: CEST(+2) Apr-Oct, CET(+1) Nov-Mar."""
    return 2 if 4 <= month <= 10 else 1


def _month_start_utc(year: int, month: int) -> datetime:
    offset_h = _cet_offset(month)
    return datetime(year, month, 1, 0, 0, 0) - timedelta(hours=offset_h)


def _month_end_utc(year: int, month: int) -> datetime:
    if month == 12:
        return _month_start_utc(year + 1, 1)
    return _month_start_utc(year, month + 1)


def _day_start_utc(year: int, month: int, day: int) -> datetime:
    offset_h = _cet_offset(month)
    return datetime(year, month, day, 0, 0, 0) - timedelta(hours=offset_h)


def _next_day_start_utc(year: int, month: int, day: int) -> datetime:
    d = date(year, month, day) + timedelta(days=1)
    return _day_start_utc(d.year, d.month, d.day)


def _all_days() -> list[tuple[int, int, int]]:
    """All calendar days from Sep 1 2025 to today (inclusive)."""
    today = date.today()
    start = date(2025, 9, 1)
    days = []
    d = start
    while d <= today:
        days.append((d.year, d.month, d.day))
        d += timedelta(days=1)
    return days


# ---------------------------------------------------------------------------
# Monthly delta computation
# ---------------------------------------------------------------------------

MONTHS = [
    (2025, 9), (2025, 10), (2025, 11), (2025, 12),
    (2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5),
]


def compute_monthly_totals() -> dict[tuple[int, int], dict[str, float | None]]:
    """Return {(year, month): {"thermal": kWh, "electrical": kWh}} using
    physical meter state column with:
      - gap interpolation at month boundaries (Jan/Feb HA-offline period)
      - pre-HA back-interpolation for Sep/Oct/early-Nov before Sensostar
        was tracked in HA.

    Pre-HA reconstruction
    ---------------------
    Both Shelly and Sensostar were commissioned at 0 kWh in Sep 2025.
    The Sensostar only appeared in HA on Nov 10 at state=2891 kWh.
    Shelly has been tracked since Sep 25 and its physical state at Nov 10
    gives us total electrical since commissioning (476.23 kWh).

    Implied average COP for commissioning -> Nov 10 = 2891 / 476.23 = 6.07.
    Monthly thermal for Sep, Oct and Nov 1-9 is derived proportionally:
        thermal_month = electrical_month * cop_preha

    This ensures the reconstructed totals close exactly on the Sensostar
    reading of 2891 kWh at the first HA entry (Nov 10).
    """
    con = _open_db()
    sh_id = _meta_id(con, SHELLY_ENTITY)
    se_id = _meta_id(con, SENSOSTAR_ENTITY)

    sh_at_nov10 = _state_at(con, sh_id, TS_SENSOSTAR_FIRST) or 476.23
    se_at_nov10 = _state_at(con, se_id, TS_SENSOSTAR_FIRST) or 2891.0
    cop_preha = se_at_nov10 / sh_at_nov10

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)
    result: dict[tuple[int, int], dict[str, float | None]] = {}

    for yr, mo in MONTHS:
        ts_start = _month_start_utc(yr, mo)
        ts_end = min(_month_end_utc(yr, mo), now_utc)

        sh_start = _state_at(con, sh_id, ts_start) if sh_id else None
        sh_end   = _state_at(con, sh_id, ts_end)   if sh_id else None
        se_start = _state_at(con, se_id, ts_start) if se_id else None
        se_end   = _state_at(con, se_id, ts_end)   if se_id else None

        if (yr, mo) == (2025, 9):
            sh_start_corr = 0.0
            el = round((sh_end or 0.0) - sh_start_corr, 2)
        elif sh_start is not None and sh_end is not None:
            el = round(sh_end - sh_start, 2)
        else:
            el = None

        if (yr, mo) in ((2025, 9), (2025, 10)):
            th = round(el * cop_preha, 1) if el is not None else None
        elif (yr, mo) == (2025, 11):
            ts_nov1  = _month_start_utc(2025, 11)
            sh_nov1  = _state_at(con, sh_id, ts_nov1) or 0.0
            sh_nov10 = sh_at_nov10
            el_preha_nov = max(sh_nov10 - sh_nov1, 0.0)
            th_preha_nov = round(el_preha_nov * cop_preha, 1)
            th_tracked = round(se_end - se_at_nov10, 1) if se_end is not None else 0.0
            th = round(th_preha_nov + th_tracked, 1)
            el_tracked = round(sh_end - sh_nov10, 2) if sh_end is not None else 0.0
            el = round(el_preha_nov + el_tracked, 2)
        elif se_start is not None and se_end is not None:
            th = round(se_end - se_start, 1)
        else:
            th = None

        result[(yr, mo)] = {"thermal": th, "electrical": el}

    con.close()
    return result


# ---------------------------------------------------------------------------
# Daily delta computation
# ---------------------------------------------------------------------------

def compute_daily_totals() -> dict[tuple[int, int, int], dict[str, float | None]]:
    """Return {(year, month, day): {"thermal": kWh, "electrical": kWh}} for all
    days from Sep 1 2025 to today.

    Uses the same pre-HA back-interpolation as compute_monthly_totals():
    - Sep 1 - Nov 9: thermal back-interpolated from electrical * cop_preha
    - Nov 10 (partial): split at first Sensostar HA entry (13:00 UTC)
    - Nov 11 onward: Sensostar state-column delta
    """
    con = _open_db()
    sh_id = _meta_id(con, SHELLY_ENTITY)
    se_id = _meta_id(con, SENSOSTAR_ENTITY)

    sh_at_nov10 = _state_at(con, sh_id, TS_SENSOSTAR_FIRST) or 476.23
    se_at_nov10 = _state_at(con, se_id, TS_SENSOSTAR_FIRST) or 2891.0
    cop_preha = se_at_nov10 / sh_at_nov10

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)
    result: dict[tuple[int, int, int], dict[str, float | None]] = {}

    for yr, mo, day in _all_days():
        ts_start = _day_start_utc(yr, mo, day)
        ts_end_full = _next_day_start_utc(yr, mo, day)
        ts_end = min(ts_end_full, now_utc)

        if ts_end <= ts_start:
            continue

        sh_start = _state_at(con, sh_id, ts_start) if sh_id else None
        sh_end   = _state_at(con, sh_id, ts_end)   if sh_id else None

        # Electrical delta
        if (yr, mo, day) == (2025, 9, 1):
            el = 0.0
        elif sh_start is not None and sh_end is not None:
            el = max(round(sh_end - sh_start, 3), 0.0)
        else:
            el = None

        # Thermal delta
        if ts_end_full <= TS_SENSOSTAR_FIRST:
            # Entire day before first Sensostar HA entry
            th = round(el * cop_preha, 2) if el is not None else None
        elif ts_start < TS_SENSOSTAR_FIRST:
            # Nov 10: partial day — pre-HA portion + tracked portion
            sh_at_split = _state_at(con, sh_id, TS_SENSOSTAR_FIRST) or sh_at_nov10
            sh_day_start_v = sh_start or sh_at_split
            el_preha = max(sh_at_split - sh_day_start_v, 0.0)
            th_preha = el_preha * cop_preha
            se_end_v = _state_at(con, se_id, ts_end) or se_at_nov10
            th_tracked = max(se_end_v - se_at_nov10, 0.0)
            th = round(th_preha + th_tracked, 3)
            el_tracked = max((sh_end or sh_at_split) - sh_at_split, 0.0)
            el = round(el_preha + el_tracked, 3)
        else:
            se_start = _state_at(con, se_id, ts_start) if se_id else None
            se_end   = _state_at(con, se_id, ts_end)   if se_id else None
            if se_start is not None and se_end is not None:
                th = max(round(se_end - se_start, 3), 0.0)
            else:
                th = None

        result[(yr, mo, day)] = {"thermal": th, "electrical": el}

    con.close()
    return result


# ---------------------------------------------------------------------------
# Statistics entry builders — monthly / yearly
# ---------------------------------------------------------------------------

def _iso(dt_utc: datetime) -> str:
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def build_monthly_stats(
    totals: dict[tuple[int, int], dict[str, float | None]],
    channel: str,
) -> list[dict]:
    """Build statistics entries for sensor.hph_{channel}_monthly.

    Each month: entry at month-start (state=0, last_reset) + month-end-1h (state=total).
    """
    stats: list[dict] = []
    cumulative = 0.0
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)

    for yr, mo in MONTHS:
        val = totals.get((yr, mo), {}).get(channel)
        if val is None:
            continue

        ts_start = _month_start_utc(yr, mo)
        ts_end = min(_month_end_utc(yr, mo) - timedelta(hours=1), now_utc)

        stats.append({"start": _iso(ts_start), "state": 0.0,           "sum": cumulative,           "last_reset": _iso(ts_start)})
        cumulative += val
        stats.append({"start": _iso(ts_end),   "state": round(val, 3), "sum": round(cumulative, 3), "last_reset": _iso(ts_start)})

    return stats


def build_yearly_stats(
    totals: dict[tuple[int, int], dict[str, float | None]],
    channel: str,
) -> list[dict]:
    """Build statistics entries for sensor.hph_{channel}_yearly."""
    season_start_utc = SEASON_START - timedelta(hours=_cet_offset(7))
    last_reset_iso = _iso(season_start_utc)

    stats: list[dict] = []
    accumulated = 0.0
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)

    for yr, mo in MONTHS:
        val = totals.get((yr, mo), {}).get(channel)
        if val is None:
            continue

        accumulated += val
        ts_end = min(_month_end_utc(yr, mo) - timedelta(hours=1), now_utc)

        stats.append({
            "start": _iso(ts_end),
            "state": round(accumulated, 3),
            "sum": round(accumulated, 3),
            "last_reset": last_reset_iso,
        })

    return stats


# ---------------------------------------------------------------------------
# Statistics entry builders — daily
# ---------------------------------------------------------------------------

def build_daily_meter_stats(
    daily_totals: dict[tuple[int, int, int], dict[str, float | None]],
    channel: str,
) -> list[dict]:
    """Build statistics entries for sensor.hph_{channel}_daily.

    Each day: entry at day-start (state=0, last_reset) + day-end-1h (state=total).
    """
    stats: list[dict] = []
    cumulative = 0.0
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)

    for yr, mo, day in _all_days():
        val = daily_totals.get((yr, mo, day), {}).get(channel)
        if val is None:
            continue

        ts_start = _day_start_utc(yr, mo, day)
        ts_end_raw = _next_day_start_utc(yr, mo, day) - timedelta(hours=1)
        ts_end = min(ts_end_raw, now_utc)

        stats.append({"start": _iso(ts_start), "state": 0.0,           "sum": cumulative,           "last_reset": _iso(ts_start)})
        cumulative += val
        stats.append({"start": _iso(ts_end),   "state": round(val, 3), "sum": round(cumulative, 3), "last_reset": _iso(ts_start)})

    return stats


def build_daily_cop_stats(
    daily_totals: dict[tuple[int, int, int], dict[str, float | None]],
) -> list[dict]:
    """Build mean-value statistics entries for sensor.hph_cop_daily.

    Imported with has_mean=True so the 'type: state, period: day' apexcharts query
    can read the daily COP value.
    """
    stats: list[dict] = []
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)

    for yr, mo, day in _all_days():
        t = daily_totals.get((yr, mo, day), {})
        th = t.get("thermal")
        el = t.get("electrical")
        # Skip days where the heat pump clearly wasn't running: standby-only
        # days have el > 0 (control electronics) but th ≈ 0, giving COP ≈ 0.
        if th is None or el is None or el < 0.05 or th < 0.3:
            continue

        cop = round(th / el, 3)
        ts_end_raw = _next_day_start_utc(yr, mo, day) - timedelta(hours=1)
        ts_end = min(ts_end_raw, now_utc)

        stats.append({"start": _iso(ts_end), "mean": cop, "min": cop, "max": cop})

    return stats


def build_monthly_cop_stats(
    totals: dict[tuple[int, int], dict[str, float | None]],
) -> list[dict]:
    """Build mean-value statistics for sensor.hph_cop_monthly (one entry per month).

    Used by the monthly COP display and by hph_cop_monthly LTS so the
    per-month COP is based on reliable Sensostar/Shelly data.
    """
    stats: list[dict] = []
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)
    for yr, mo in MONTHS:
        t = totals.get((yr, mo), {})
        th = t.get("thermal")
        el = t.get("electrical")
        if th is None or el is None or el < 0.05 or th < 0.3:
            continue
        cop = round(th / el, 3)
        ts_end = min(_month_end_utc(yr, mo) - timedelta(hours=1), now_utc)
        stats.append({"start": _iso(ts_end), "mean": cop, "min": cop, "max": cop})
    return stats


def build_scop_stats(
    totals: dict[tuple[int, int], dict[str, float | None]],
) -> list[dict]:
    """Build mean-value statistics for sensor.hph_scop (one entry per month,
    showing the cumulative seasonal SCOP up to that month).

    The SCOP chart reads type:mean,period:month so each bar shows the
    running SCOP for the heating season Jul-Jun.
    """
    stats: list[dict] = []
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)
    th_acc = el_acc = 0.0
    for yr, mo in MONTHS:
        t = totals.get((yr, mo), {})
        th = t.get("thermal")
        el = t.get("electrical")
        if th is None or el is None:
            continue
        th_acc += th
        el_acc += el
        if el_acc < 0.05:
            continue
        scop = round(th_acc / el_acc, 3)
        ts_end = min(_month_end_utc(yr, mo) - timedelta(hours=1), now_utc)
        stats.append({"start": _iso(ts_end), "mean": scop, "min": scop, "max": scop})
    return stats


# ---------------------------------------------------------------------------
# Statistics entry builder — hourly cumulative (energy_active)
# ---------------------------------------------------------------------------

def build_hourly_energy_stats(
    con: sqlite3.Connection,
    meta_id: int,
    channel: str,  # "thermal" | "electrical"
    sh_at_nov10: float,
    se_at_nov10: float,
    cop_preha: float,
    sh_id: int | None,
) -> list[dict]:
    """Build hourly LTS entries for sensor.hph_{channel}_energy_active.

    For thermal (Sensostar):
      - Nov 10 13:00 UTC onward: raw DB state values (physical meter reading)
      - Before Nov 10: prepend reconstructed hourly values using Shelly * cop_preha

    For electrical (Shelly):
      - All available DB rows from Sep 25 onward
    """
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)

    if channel == "thermal":
        rows = _load_all_rows(con, meta_id, TS_SENSOSTAR_FIRST)
        # Prepend pre-HA reconstructed hourly values (Sep 25 - Nov 10)
        # Use Shelly hourly rows to drive the timeline, scale by cop_preha
        pre_entries: list[dict] = []
        if sh_id is not None:
            ts_shelly_start = datetime(2025, 9, 25, 0, 0, 0)  # Shelly first HA entry approx
            sh_rows = _load_all_rows(con, sh_id, ts_shelly_start)
            # sh_rows contains absolute meter readings; first entry is ~50 kWh
            # commissioning was at 0 kWh, so offset = first_shelly_state
            sh_offset = sh_rows[0][1] if sh_rows else 0.0  # meter reading at first HA entry
            # Derive pre-HA thermal: thermal_cumulative = (sh_state - sh_offset) * cop_preha
            for ts_epoch, sh_state in sh_rows:
                ts_dt = datetime.utcfromtimestamp(ts_epoch)
                if ts_dt >= TS_SENSOSTAR_FIRST:
                    break
                thermal_val = round((sh_state - sh_offset) * cop_preha, 3)
                pre_entries.append({
                    "start": _iso(ts_dt),
                    "state": thermal_val,
                    "sum": thermal_val,
                })
        # Append actual Sensostar rows
        for ts_epoch, se_state in rows:
            ts_dt = datetime.utcfromtimestamp(ts_epoch)
            if ts_dt > now_utc:
                break
            pre_entries.append({
                "start": _iso(ts_dt),
                "state": round(se_state, 3),
                "sum": round(se_state, 3),
            })
        return pre_entries

    else:  # electrical
        ts_shelly_start = datetime(2025, 9, 25, 0, 0, 0)
        rows = _load_all_rows(con, meta_id, ts_shelly_start)
        entries: list[dict] = []
        for ts_epoch, sh_state in rows:
            ts_dt = datetime.utcfromtimestamp(ts_epoch)
            if ts_dt > now_utc:
                break
            entries.append({
                "start": _iso(ts_dt),
                "state": round(sh_state, 3),
                "sum": round(sh_state, 3),
            })
        return entries


# ---------------------------------------------------------------------------
# WebSocket import
# ---------------------------------------------------------------------------

def _ws_connect():
    """Open an authenticated WebSocket connection, return ws object."""
    import urllib.parse
    parsed = urllib.parse.urlparse(HA_BASE)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = f"{ws_scheme}://{parsed.netloc}/api/websocket"

    ws = websocket.create_connection(ws_url, timeout=60)
    auth_required = json.loads(ws.recv())
    assert auth_required["type"] == "auth_required", auth_required
    ws.send(json.dumps({"type": "auth", "access_token": HA_TOKEN}))
    auth_ok = json.loads(ws.recv())
    if auth_ok.get("type") != "auth_ok":
        ws.close()
        raise RuntimeError(f"WebSocket auth failed: {auth_ok}")
    return ws


def ws_clear(statistic_ids: list[str]) -> bool:
    """Delete all existing LTS rows for the given statistic IDs.

    Must be called before re-importing data into entities that already have
    LTS entries, to avoid backwards-sum conflicts that cause HA to silently
    reject the new rows.
    """
    try:
        ws = _ws_connect()
        ws.send(json.dumps({
            "id": 1,
            "type": "recorder/clear_statistics",
            "statistic_ids": statistic_ids,
        }))
        result = json.loads(ws.recv())
        ws.close()
        return result.get("success", False)
    except Exception as exc:
        print(f"  ws_clear error: {exc}", file=sys.stderr)
        return False


def ws_import(
    entity_id: str,
    stats: list[dict],
    unit: str = "kWh",
    has_sum: bool = True,
    has_mean: bool = False,
) -> bool:
    # Split large imports into chunks to avoid WebSocket message-size issues
    CHUNK = 500
    if len(stats) > CHUNK:
        for i in range(0, len(stats), CHUNK):
            chunk = stats[i:i + CHUNK]
            if not ws_import(entity_id, chunk, unit=unit, has_sum=has_sum, has_mean=has_mean):
                return False
        return True

    try:
        ws = _ws_connect()
    except RuntimeError as exc:
        print(f"  {exc}", file=sys.stderr)
        return False

    msg = {
        "id": 1,
        "type": "recorder/import_statistics",
        "metadata": {
            "has_mean": has_mean,
            "has_sum": has_sum,
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
    ap.add_argument("--full", action="store_true",
                    help="Also import daily totals and hourly cumulative energy (fills 30-day charts)")
    args = ap.parse_args()

    if args.confirm and not HA_TOKEN:
        print("ERROR: HA_TOKEN required for --confirm mode", file=sys.stderr)
        return 1

    mode = "LIVE IMPORT" if args.confirm else "DRY RUN (add --confirm to write)"
    resolution = " + DAILY + HOURLY" if args.full else " (monthly only)"
    print(f"\nHPH Backfill -- {mode}{resolution}")
    print(f"DB: {HA_DB}")
    print(f"HA: {HA_BASE}\n")

    # -- Monthly totals (always) -------------------------------------------
    totals = compute_monthly_totals()

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
        if _month_end_utc(yr, mo) > now_utc:
            partial = " (partial)"
        print(f"{yr}-{mo:02d}    {th_str}  {el_str}  {cop_str}{partial}")
        if th:
            th_total += th
        if el:
            el_total += el
    print("-" * 44)
    scop = th_total / el_total if el_total > 0 else 0
    print(f"{'TOTAL':<10}  {th_total:10.0f}  {el_total:10.1f}  {scop:6.2f}  (SCOP)\n")

    # Build monthly/yearly stat sets
    # (entity_id, stats, label, has_sum, has_mean, unit)
    targets: list[tuple[str, list[dict], str, bool, bool, str]] = [
        (HPH_THERMAL_MONTHLY,    build_monthly_stats(totals, "thermal"),    "monthly",          True,  False, "kWh"),
        (HPH_ELECTRICAL_MONTHLY, build_monthly_stats(totals, "electrical"), "monthly",          True,  False, "kWh"),
        (HPH_THERMAL_YEARLY,     build_yearly_stats(totals,  "thermal"),    "yearly",           True,  False, "kWh"),
        (HPH_ELECTRICAL_YEARLY,  build_yearly_stats(totals,  "electrical"), "yearly",           True,  False, "kWh"),
        (HPH_COP_MONTHLY,        build_monthly_cop_stats(totals),           "monthly COP",      False, True,  "x"),
        (HPH_SCOP,               build_scop_stats(totals),                  "seasonal SCOP",    False, True,  "x"),
    ]

    # -- Daily totals (--full) --------------------------------------------
    if args.full:
        print("Computing daily totals (this may take ~10 seconds)...")
        daily_totals = compute_daily_totals()
        day_count = len([v for v in daily_totals.values() if v["thermal"] is not None])
        print(f"  {day_count} days with data\n")

        targets += [
            (HPH_THERMAL_DAILY,    build_daily_meter_stats(daily_totals, "thermal"),    "daily",     True,  False, "kWh"),
            (HPH_ELECTRICAL_DAILY, build_daily_meter_stats(daily_totals, "electrical"), "daily",     True,  False, "kWh"),
            (HPH_COP_DAILY,        build_daily_cop_stats(daily_totals),                 "daily COP", False, True,  "x"),
        ]

    # -- Hourly cumulative (--full) ----------------------------------------
    if args.full:
        con = _open_db()
        sh_id = _meta_id(con, SHELLY_ENTITY)
        se_id = _meta_id(con, SENSOSTAR_ENTITY)
        sh_at_nov10 = _state_at(con, sh_id, TS_SENSOSTAR_FIRST) or 476.23
        se_at_nov10 = _state_at(con, se_id, TS_SENSOSTAR_FIRST) or 2891.0
        cop_preha = se_at_nov10 / sh_at_nov10

        th_hourly = build_hourly_energy_stats(con, se_id, "thermal",    sh_at_nov10, se_at_nov10, cop_preha, sh_id)
        el_hourly = build_hourly_energy_stats(con, sh_id, "electrical", sh_at_nov10, se_at_nov10, cop_preha, sh_id)
        con.close()

        targets += [
            (HPH_THERMAL_ENERGY_ACTIVE,    th_hourly, "hourly cumulative", True, False, "kWh"),
            (HPH_ELECTRICAL_ENERGY_ACTIVE, el_hourly, "hourly cumulative", True, False, "kWh"),
        ]

    # -- Clear existing LTS before re-import ---------------------------------
    # HA's recorder/import_statistics silently rejects historical entries when
    # existing LTS rows have a higher sum than the imported historical rows
    # (backwards-sum conflict). Clearing first lets the import write cleanly.
    if args.confirm:
        # COP/SCOP are mean-only (no sum), but clear anyway so stale rows don't
        # show up in charts after a re-run with different thresholds.
        cop_ids = [HPH_COP_MONTHLY, HPH_SCOP]
        print("-- Clearing existing monthly COP/SCOP LTS ---------------------------")
        ok = ws_clear(cop_ids)
        print(f"  clear: {'OK' if ok else 'FAILED'}")
        print()

    if args.confirm and args.full:
        clear_ids = [
            HPH_THERMAL_DAILY, HPH_ELECTRICAL_DAILY, HPH_COP_DAILY,
            HPH_THERMAL_ENERGY_ACTIVE, HPH_ELECTRICAL_ENERGY_ACTIVE,
        ]
        print("-- Clearing existing daily/hourly LTS (avoids sum-conflict) --------")
        ok = ws_clear(clear_ids)
        print(f"  clear: {'OK' if ok else 'FAILED'}")
        print()

    # -- Print + import all targets ----------------------------------------
    print("-- Import targets ---------------------------------------------------")
    for entity_id, stats, meter_type, has_sum, has_mean, unit in targets:
        print(f"  {entity_id}  ({meter_type})  --> {len(stats)} entries")
        if args.confirm:
            ok = ws_import(entity_id, stats, unit=unit, has_sum=has_sum, has_mean=has_mean)
            print(f"    {'OK' if ok else 'FAILED'}")
        else:
            if stats:
                print(f"    first: {stats[0]}")
                print(f"    last:  {stats[-1]}")

    if not args.confirm:
        print("\nDry-run complete. Run with --confirm to write to HA.")
    else:
        print("\nImport complete.")
        if args.full:
            print("  - 30-day bar charts (thermal/electrical) now have historical daily data")
            print("  - COP trend chart now has 8 months of daily COP history")
            print("  - Statistics-graph chart now has hourly cumulative data")
        print("Reload the HPH integration or restart HA if entity states look stale.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
