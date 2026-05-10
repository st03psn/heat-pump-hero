#!/usr/bin/env python3
"""
HeatPump Hero — backfill HPH statistics from existing energy counter sensors.

Reads historical long-term statistics from your existing monthly energy
sensors (e.g. sensor.wp_waerme_kwh_monat, sensor.wp_strom_kwh_monat) via
the HA recorder/statistics_during_period WebSocket API and imports them into
the corresponding HPH entity statistics (sensor.hph_thermal_monthly,
sensor.hph_electrical_monthly, sensor.hph_cop_monthly).

No CSV export step needed — reads and writes live against your HA instance.

Requirements:
    pip install websocket-client

Usage:
    HA_BASE_URL=http://192.168.111.73:8123 \\
    HA_TOKEN=eyJhb... \\
    python3 hph_import_legacy_stats.py --dry-run

    # If your source sensors have different entity IDs:
    HA_BASE_URL=http://192.168.111.73:8123 \\
    HA_TOKEN=eyJhb... \\
    python3 hph_import_legacy_stats.py \\
        --thermal-src sensor.my_heat_meter_monthly \\
        --elec-src sensor.my_power_meter_monthly \\
        --months 18 --dry-run

Notes:
    - Source sensors must have long-term statistics in HA recorder.
      (state_class: total or total_increasing, utility_meter, or similar)
    - The script uses the monthly 'change' value (delta per month) from
      the source statistics — works for both cumulative and resetting counters.
    - Target entities must already exist (HPH must be set up first).
    - Run with --dry-run first to verify the numbers before writing.
    - HA rejects statistics that overlap existing data — safe to run twice.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone, timedelta

try:
    import websocket  # pip install websocket-client
except ImportError:
    print("websocket-client not installed.  pip install websocket-client", file=sys.stderr)
    sys.exit(1)


# ── Default mapping ──────────────────────────────────────────────────────────
DEFAULTS = {
    "thermal_src": "sensor.wp_waerme_kwh_monat",
    "elec_src": "sensor.wp_strom_kwh_monat",
    "thermal_dst": "sensor.hph_thermal_monthly",
    "elec_dst": "sensor.hph_electrical_monthly",
    "cop_dst": "sensor.hph_cop_monthly",
}


def _ws_connect(base_url: str, token: str) -> websocket.WebSocket:
    parsed = urllib.parse.urlparse(base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = f"{ws_scheme}://{parsed.netloc}/api/websocket"
    ws = websocket.create_connection(ws_url, timeout=30)
    hello = json.loads(ws.recv())
    assert hello["type"] == "auth_required", f"unexpected: {hello}"
    ws.send(json.dumps({"type": "auth", "access_token": token}))
    auth_ok = json.loads(ws.recv())
    if auth_ok.get("type") != "auth_ok":
        print(f"authentication failed: {auth_ok}", file=sys.stderr)
        ws.close()
        sys.exit(1)
    return ws


_msg_counter = 0


def _next_id() -> int:
    global _msg_counter
    _msg_counter += 1
    return _msg_counter


def _fetch_monthly_stats(ws: websocket.WebSocket, entity_id: str, months: int) -> list[dict]:
    """Fetch monthly aggregated statistics for entity_id going back <months>."""
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=months * 31)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    req = {
        "id": _next_id(),
        "type": "recorder/statistics_during_period",
        "statistic_ids": [entity_id],
        "start_time": start.isoformat(),
        "period": "month",
        "units": {"energy": "kWh"},
    }
    ws.send(json.dumps(req))
    resp = json.loads(ws.recv())
    if not resp.get("success"):
        print(f"  ERROR fetching {entity_id}: {resp}", file=sys.stderr)
        return []
    stats = resp.get("result", {}).get(entity_id, [])
    return stats


def _import_statistics(
    ws: websocket.WebSocket,
    statistic_id: str,
    name: str,
    unit: str,
    rows: list[dict],
    has_mean: bool = False,
) -> bool:
    """Send recorder/import_statistics for the given rows."""
    msg = {
        "id": _next_id(),
        "type": "recorder/import_statistics",
        "metadata": {
            "has_mean": has_mean,
            "has_sum": not has_mean,
            "name": name,
            "source": "recorder",
            "statistic_id": statistic_id,
            "unit_of_measurement": unit,
        },
        "stats": rows,
    }
    ws.send(json.dumps(msg))
    result = json.loads(ws.recv())
    return bool(result.get("success"))


def main() -> int:
    p = argparse.ArgumentParser(description="Backfill HPH statistics from existing energy sensors")
    p.add_argument("--thermal-src", default=DEFAULTS["thermal_src"],
                   help=f"Source thermal entity (default: {DEFAULTS['thermal_src']})")
    p.add_argument("--elec-src", default=DEFAULTS["elec_src"],
                   help=f"Source electrical entity (default: {DEFAULTS['elec_src']})")
    p.add_argument("--thermal-dst", default=DEFAULTS["thermal_dst"],
                   help=f"Target thermal entity (default: {DEFAULTS['thermal_dst']})")
    p.add_argument("--elec-dst", default=DEFAULTS["elec_dst"],
                   help=f"Target electrical entity (default: {DEFAULTS['elec_dst']})")
    p.add_argument("--cop-dst", default=DEFAULTS["cop_dst"],
                   help=f"Target COP entity (default: {DEFAULTS['cop_dst']})")
    p.add_argument("--months", type=int, default=24,
                   help="How many months to look back (default: 24)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would be imported without writing anything")
    args = p.parse_args()

    base_url = os.environ.get("HA_BASE_URL", "http://homeassistant.local:8123").rstrip("/")
    token = os.environ.get("HA_TOKEN")
    if not token:
        print("HA_TOKEN environment variable required", file=sys.stderr)
        return 1

    mode = "DRY RUN" if args.dry_run else "LIVE IMPORT"
    print(f"\nHeatPump Hero legacy stats backfill — {mode}")
    print(f"  HA instance : {base_url}")
    print(f"  Thermal     : {args.thermal_src} -> {args.thermal_dst}")
    print(f"  Electrical  : {args.elec_src} -> {args.elec_dst}")
    print(f"  COP         : computed -> {args.cop_dst}")
    print(f"  Look-back   : {args.months} months\n")

    ws = _ws_connect(base_url, token)
    print("Connected and authenticated.")

    # Fetch source stats
    thermal_raw = _fetch_monthly_stats(ws, args.thermal_src, args.months)
    elec_raw = _fetch_monthly_stats(ws, args.elec_src, args.months)
    ws.close()

    if not thermal_raw:
        print(f"No statistics found for {args.thermal_src}. "
              "Check entity ID and that it has long-term statistics.", file=sys.stderr)
        return 1
    if not elec_raw:
        print(f"No statistics found for {args.elec_src}. "
              "Check entity ID and that it has long-term statistics.", file=sys.stderr)
        return 1

    # Build month-keyed dicts using 'change' (monthly delta) or 'sum' delta
    def monthly_kwh(raw: list[dict]) -> dict[str, float]:
        """Extract monthly kWh values. Prefer 'change'; fall back to 'sum' delta.
        'start' field from HA WebSocket is a Unix timestamp (integer seconds)."""
        result: dict[str, float] = {}
        prev_sum = None
        for entry in raw:
            ts_raw = entry.get("start")
            if ts_raw is None:
                continue
            # HA returns milliseconds; convert to seconds
            ts_sec = int(ts_raw) / 1000
            dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
            month_key = dt.strftime("%Y-%m")
            iso_start = dt.strftime("%Y-%m-01T00:00:00+00:00")
            if "change" in entry and entry["change"] is not None:
                result[month_key] = (round(float(entry["change"]), 3), iso_start)
            elif "sum" in entry and entry["sum"] is not None:
                s = float(entry["sum"])
                if prev_sum is not None:
                    result[month_key] = (round(max(s - prev_sum, 0.0), 3), iso_start)
                prev_sum = s
        return result

    t_by_month = monthly_kwh(thermal_raw)
    e_by_month = monthly_kwh(elec_raw)

    # Find months present in both sources
    months_both = sorted(set(t_by_month) & set(e_by_month))
    if not months_both:
        print("No overlapping months between thermal and electrical sources.", file=sys.stderr)
        return 1

    print(f"{'Month':<10} {'Thermal kWh':>12} {'Electrical kWh':>14} {'COP':>6}")
    print("-" * 46)

    thermal_rows: list[dict] = []
    elec_rows: list[dict] = []
    cop_rows: list[dict] = []
    t_cumsum = 0.0
    e_cumsum = 0.0

    for month in months_both:
        t_kwh, start_ts = t_by_month[month]
        e_kwh, _       = e_by_month[month]
        cop = round(t_kwh / e_kwh, 3) if e_kwh > 0.1 else 0.0
        t_cumsum += t_kwh
        e_cumsum += e_kwh

        thermal_rows.append({"start": start_ts, "state": t_kwh, "sum": round(t_cumsum, 3)})
        elec_rows.append({"start": start_ts, "state": e_kwh, "sum": round(e_cumsum, 3)})
        # COP is a measurement (no sum): only 'mean' / 'state'
        cop_rows.append({"start": start_ts, "state": cop, "mean": cop})

        tag = "  ← " if cop < 1.5 else ""
        print(f"{month:<10} {t_kwh:>12.3f} {e_kwh:>14.3f} {cop:>6.2f}{tag}")

    print(f"\nTotal: {len(months_both)} months  |  "
          f"Thermal {t_cumsum:.1f} kWh  |  Electrical {e_cumsum:.1f} kWh  |  "
          f"Overall COP {t_cumsum/e_cumsum:.2f}")

    if args.dry_run:
        print("\n-- DRY RUN -- nothing written. Re-run without --dry-run to import.")
        return 0

    print("\nImporting ...")
    ws2 = _ws_connect(base_url, token)

    ok_t = _import_statistics(ws2, args.thermal_dst, "HPH Thermal Monthly", "kWh", thermal_rows)
    ok_e = _import_statistics(ws2, args.elec_dst, "HPH Electrical Monthly", "kWh", elec_rows)

    # COP: has_mean=True, no sum
    cop_stats = [{"start": r["start"], "mean": r["mean"], "state": r["state"]} for r in cop_rows]
    ok_c = _import_statistics(ws2, args.cop_dst, "HPH COP Monthly", "x", cop_stats, has_mean=True)

    ws2.close()

    print(f"  {args.thermal_dst}: {'OK' if ok_t else 'FAILED'}")
    print(f"  {args.elec_dst}:    {'OK' if ok_e else 'FAILED'}")
    print(f"  {args.cop_dst}:      {'OK' if ok_c else 'FAILED'}")

    if ok_t and ok_e and ok_c:
        print("\nDone. Reload the HPH dashboard — monthly COP and energy charts "
              "should now show historical data.")
        return 0
    else:
        print("\nPartial failure — check HA logs for details.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
