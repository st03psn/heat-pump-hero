#!/usr/bin/env python3
"""HeatPump Hero — plausibility check script.

Queries HA REST API and compares HPH computed values against the real
Shelly 3EM and Sensostar WMZ ground truth sensors.

Usage:
    python scripts/check_plausibility.py

Environment variables:
    HA_BASE_URL   e.g. http://homeassistant.local:8123  (default: http://192.168.111.73:8123)
    HA_TOKEN      long-lived access token (mandatory)

What it checks
--------------
1. Live power: HPH electrical/thermal vs. Shelly/Sensostar
2. Daily energy: HPH daily totals vs. today's delta on the external meters
3. COP: HPH COP vs. manual thermal/electrical ratio
4. Standby breakdown: runtime + standby must sum to total daily kWh
5. Source mode: verifies external_energy mode is active for both channels
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone
from typing import Any

HA_BASE = os.environ.get("HA_BASE_URL", "http://192.168.111.73:8123").rstrip("/")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

# Ground-truth external sensors (Shelly 3EM + Sensostar WMZ)
GT_ELECTRICAL_POWER = "sensor.3em_wpaussen_total_active_power"       # W
GT_ELECTRICAL_ENERGY = "sensor.3em_wpaussen_total_active_energy"     # kWh, total_increasing
GT_THERMAL_POWER = "sensor.sensostar_9ce898_sensostar_calculated_power"  # W
GT_THERMAL_ENERGY = "sensor.sensostar_9ce898_sensostar_energy"        # kWh, total_increasing

# HPH computed entities
HPH_ELECTRICAL_POWER = "sensor.hph_electrical_power_active"
HPH_THERMAL_POWER = "sensor.hph_thermal_power_active"
HPH_ELECTRICAL_DAILY = "sensor.hph_electrical_daily"
HPH_THERMAL_DAILY = "sensor.hph_thermal_daily"
HPH_COP_LIVE = "sensor.hph_cop_live"
HPH_COP_DAILY = "sensor.hph_cop_daily"
HPH_ELECTRICAL_RUNTIME = "number.hph_electrical_runtime_today_kwh"
HPH_THERMAL_RUNTIME = "number.hph_thermal_runtime_today_kwh"
HPH_STANDBY_ELECTRICAL = "sensor.hph_standby_electrical_daily"
HPH_ELECTRICAL_SOURCE = "select.hph_electrical_source"
HPH_THERMAL_SOURCE = "select.hph_thermal_source"
HPH_COMPRESSOR = "binary_sensor.hph_compressor_running"

# Shelly daily-reset reference: energy at midnight (for today's delta)
# We derive today's delta from HA's history endpoint.
HISTORY_ENTITIES = [GT_ELECTRICAL_ENERGY, GT_THERMAL_ENERGY]


def _get(path: str) -> Any:
    url = f"{HA_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def state(entity_id: str) -> str:
    try:
        return _get(f"/api/states/{entity_id}")["state"]
    except Exception as exc:  # noqa: BLE001
        return f"ERROR({exc})"


def flt(val: str) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def today_start_iso() -> str:
    """ISO-8601 timestamp for 00:00:00 local time today (UTC offset-naive, HA accepts both)."""
    today = date.today()
    midnight = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    return midnight.isoformat()


def today_delta(entity_id: str) -> float | None:
    """Energy accumulated today = current_value − value_at_midnight.

    Uses HA REST history endpoint to get the first state record after midnight.
    """
    start = today_start_iso()
    try:
        data = _get(f"/api/history/period/{start}?filter_entity_id={entity_id}&minimal_response=true")
        if not data or not data[0]:
            return None
        first_val = flt(data[0][0]["state"])
        current_val = flt(state(entity_id))
        if first_val is None or current_val is None:
            return None
        return max(current_val - first_val, 0.0)
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] history query failed for {entity_id}: {exc}")
        return None


def pct_diff(a: float, b: float) -> str:
    if b == 0:
        return "N/A"
    return f"{(a - b) / b * 100:+.1f}%"


def ok_warn(val: float, threshold: float = 0.05) -> str:
    return "OK" if abs(val) <= threshold else "WARN"


# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    if not HA_TOKEN:
        print("ERROR: set HA_TOKEN environment variable (long-lived access token)")
        sys.exit(1)

    print(f"\nHeatPump Hero — Plausibility Check  [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print(f"HA: {HA_BASE}\n")

    # ── 0. Source modes ─────────────────────────────────────────────────────
    print("── Source modes ─────────────────────────────────────────────────")
    el_src = state(HPH_ELECTRICAL_SOURCE)
    th_src = state(HPH_THERMAL_SOURCE)
    el_ok = el_src == "external_energy"
    th_ok = th_src == "external_energy"
    print(f"  Electrical source : {el_src:30s}  {'OK' if el_ok else 'WARN — expected external_energy'}")
    print(f"  Thermal source    : {th_src:30s}  {'OK' if th_ok else 'WARN — expected external_energy'}")
    print()

    # ── 1. Live power ────────────────────────────────────────────────────────
    print("── Live power [W] ───────────────────────────────────────────────")
    comp = state(HPH_COMPRESSOR)
    print(f"  Compressor        : {comp}")

    gt_el_w = flt(state(GT_ELECTRICAL_POWER))
    hph_el_w = flt(state(HPH_ELECTRICAL_POWER))
    gt_th_w = flt(state(GT_THERMAL_POWER))
    hph_th_w = flt(state(HPH_THERMAL_POWER))

    print(f"\n  Electrical [W]")
    print(f"    Shelly 3EM      : {gt_el_w}")
    print(f"    HPH computed    : {hph_el_w}")
    if gt_el_w and hph_el_w:
        diff_pct = pct_diff(hph_el_w, gt_el_w)
        rel = abs(hph_el_w - gt_el_w) / max(gt_el_w, 1)
        print(f"    Deviation       : {diff_pct}  → {ok_warn(rel)}")

    print(f"\n  Thermal [W]")
    print(f"    Sensostar       : {gt_th_w}")
    print(f"    HPH computed    : {hph_th_w}")
    if gt_th_w and hph_th_w:
        diff_pct = pct_diff(hph_th_w, gt_th_w)
        rel = abs(hph_th_w - gt_th_w) / max(gt_th_w, 1)
        print(f"    Deviation       : {diff_pct}  → {ok_warn(rel, 0.10)}")
    print()

    # ── 2. Today's energy totals ─────────────────────────────────────────────
    print("── Daily energy [kWh] ───────────────────────────────────────────")
    print("  (fetching today's delta from HA history — may take a moment…)")
    gt_el_day = today_delta(GT_ELECTRICAL_ENERGY)
    gt_th_day = today_delta(GT_THERMAL_ENERGY)
    hph_el_day = flt(state(HPH_ELECTRICAL_DAILY))
    hph_th_day = flt(state(HPH_THERMAL_DAILY))

    print(f"\n  Electrical [kWh]")
    print(f"    Shelly delta    : {gt_el_day}")
    print(f"    HPH daily       : {hph_el_day}")
    if gt_el_day is not None and hph_el_day is not None:
        diff = hph_el_day - gt_el_day
        diff_pct = pct_diff(hph_el_day, gt_el_day)
        rel = abs(diff) / max(gt_el_day, 0.01)
        print(f"    Deviation       : {diff:+.3f} kWh  {diff_pct}  → {ok_warn(rel)}")

    print(f"\n  Thermal [kWh]")
    print(f"    Sensostar delta : {gt_th_day}")
    print(f"    HPH daily       : {hph_th_day}")
    if gt_th_day is not None and hph_th_day is not None:
        diff = hph_th_day - gt_th_day
        diff_pct = pct_diff(hph_th_day, gt_th_day)
        rel = abs(diff) / max(gt_th_day, 0.01)
        print(f"    Deviation       : {diff:+.3f} kWh  {diff_pct}  → {ok_warn(rel)}")
    print()

    # ── 3. COP ───────────────────────────────────────────────────────────────
    print("── COP ──────────────────────────────────────────────────────────")
    hph_cop_live = flt(state(HPH_COP_LIVE))
    hph_cop_day = flt(state(HPH_COP_DAILY))

    if gt_el_w and gt_th_w and gt_el_w > 10:
        gt_cop_live = gt_th_w / gt_el_w
        print(f"  Live COP (ground truth) : {gt_cop_live:.2f}")
        print(f"  Live COP (HPH)          : {hph_cop_live}")
        if hph_cop_live:
            print(f"  Deviation               : {pct_diff(hph_cop_live, gt_cop_live)}")
    else:
        print(f"  Live COP (HPH)          : {hph_cop_live}  (ground truth unavailable — compressor off?)")

    if gt_el_day and gt_th_day and gt_el_day > 0.01:
        gt_cop_day = gt_th_day / gt_el_day
        print(f"  Daily COP (ground truth): {gt_cop_day:.2f}")
        print(f"  Daily COP (HPH)         : {hph_cop_day}")
        if hph_cop_day:
            print(f"  Deviation               : {pct_diff(float(hph_cop_day), gt_cop_day)}")
    print()

    # ── 4. Standby breakdown ─────────────────────────────────────────────────
    print("── Standby breakdown ────────────────────────────────────────────")
    hph_el_runtime = flt(state(HPH_ELECTRICAL_RUNTIME))
    hph_th_runtime = flt(state(HPH_THERMAL_RUNTIME))
    hph_standby = flt(state(HPH_STANDBY_ELECTRICAL))

    print(f"  HPH electrical daily    : {hph_el_day}")
    print(f"  HPH electrical runtime  : {hph_el_runtime}")
    print(f"  HPH standby electrical  : {hph_standby}")
    if hph_el_day is not None and hph_el_runtime is not None:
        computed_standby = max(hph_el_day - hph_el_runtime, 0)
        print(f"  Standby (computed)      : {computed_standby:.3f}")
        if hph_standby is not None:
            delta = abs(hph_standby - computed_standby)
            print(f"  Sensor vs computed delta: {delta:.3f} kWh  → {'OK' if delta < 0.01 else 'WARN'}")
    if gt_el_day is not None and hph_el_runtime is not None:
        gt_standby = max(gt_el_day - hph_el_runtime, 0)
        print(f"  GT standby (Shelly-runtime): {gt_standby:.3f} kWh")
    print()

    # ── 5. Summary ───────────────────────────────────────────────────────────
    print("── Summary ──────────────────────────────────────────────────────")
    checks = []
    if gt_el_day is not None and hph_el_day is not None and gt_el_day > 0.01:
        checks.append(("Electrical daily", abs(hph_el_day - gt_el_day) / gt_el_day, 0.05))
    if gt_th_day is not None and hph_th_day is not None and gt_th_day > 0.01:
        checks.append(("Thermal daily", abs(hph_th_day - gt_th_day) / gt_th_day, 0.10))
    if not el_ok:
        print("  WARN  Electrical source is not external_energy → totals unreliable")
    if not th_ok:
        print("  WARN  Thermal source is not external_energy → totals unreliable")
    for name, rel, threshold in checks:
        status = "OK  " if rel <= threshold else "WARN"
        print(f"  {status}  {name}: {rel * 100:.1f}% deviation (threshold {threshold * 100:.0f}%)")
    if not checks:
        print("  No ground-truth data available for comparison.")
    print()


if __name__ == "__main__":
    main()
