#!/usr/bin/env python3
"""
Heat Pump Hero — heating curve regression analysis (Layer 2).

Fits a linear regression supply_temp = a + b * outdoor_temp over the last
N days of HA history and writes a plain-language recommendation to
input_text.hph_heating_curve_recommendation. The advisor surfaces it.

Approach:
  1. Pull `sensor.hph_source_outlet_temp` and
     `sensor.hph_source_outdoor_temp` history from HA REST API
  2. Filter to compressor-on samples only (uses
     binary_sensor.hph_compressor_running)
  3. Compute least-squares slope / intercept
  4. Compare against ideal slopes for typical building types and
     output a recommendation

This is offline analysis — runs nightly via shell_command, or manually
on demand. No ML library required (uses stdlib + numpy if available).

Usage:
  HA_BASE_URL=http://homeassistant.local:8123 \\
  HA_TOKEN=<long-lived> \\
  python3 analyze_heating_curve.py [--days 14]
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone


def fetch_history(base_url: str, token: str, entity: str, start: datetime) -> list[dict]:
    url = f"{base_url}/api/history/period/{start.isoformat()}?filter_entity_id={entity}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data[0] if data else []


def parse_ts(s: str) -> datetime:
    # HA returns ISO8601 with timezone
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def align(supply: list[dict], outdoor: list[dict], compressor: list[dict],
          tolerance_s: int = 60) -> list[tuple[float, float]]:
    """Return list of (outdoor, supply) pairs sampled while compressor was on."""
    # Build sorted compressor-on intervals
    intervals: list[tuple[datetime, datetime]] = []
    on_start: datetime | None = None
    for ev in sorted(compressor, key=lambda x: x["last_changed"]):
        ts = parse_ts(ev["last_changed"])
        if ev["state"] in ("on", "True", "true"):
            if on_start is None:
                on_start = ts
        else:
            if on_start is not None:
                intervals.append((on_start, ts))
                on_start = None
    if on_start is not None:
        intervals.append((on_start, datetime.now(timezone.utc)))

    def is_compressor_on(t: datetime) -> bool:
        for s, e in intervals:
            if s <= t <= e:
                return True
        return False

    # Index outdoor by timestamp
    out_pairs = [(parse_ts(o["last_changed"]), float(o["state"]))
                 for o in outdoor if o["state"] not in ("unknown", "unavailable", "none")]
    out_pairs.sort()

    pairs: list[tuple[float, float]] = []
    for s in supply:
        if s["state"] in ("unknown", "unavailable", "none"):
            continue
        t = parse_ts(s["last_changed"])
        if not is_compressor_on(t):
            continue
        # Find nearest outdoor reading within tolerance
        candidates = [(t - ot[0], ot[1]) for ot in out_pairs
                      if abs((t - ot[0]).total_seconds()) <= tolerance_s]
        if not candidates:
            continue
        _, outdoor_val = min(candidates, key=lambda x: abs(x[0].total_seconds()))
        try:
            pairs.append((outdoor_val, float(s["state"])))
        except (TypeError, ValueError):
            continue
    return pairs


def least_squares(pairs: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Return (slope, intercept, r2) for y = slope * x + intercept."""
    n = len(pairs)
    if n < 10:
        return 0.0, 0.0, 0.0
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x == 0:
        return 0.0, mean_y, 0.0
    slope = cov / var_x
    intercept = mean_y - slope * mean_x
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_y == 0:
        r2 = 1.0
    else:
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in pairs)
        r2 = 1.0 - ss_res / var_y
    return slope, intercept, r2


def recommend(slope: float, intercept: float, r2: float, n: int) -> str:
    """Translate regression into plain-language recommendation."""
    if n < 30:
        return f"insufficient data ({n} samples) — need at least 30 compressor-on samples"
    if r2 < 0.4:
        return (f"low correlation (R²={r2:.2f}) — heating-curve relation noisy. "
                f"Possibly room thermostat overrides curve, or compressor cycles too short.")
    # Typical good slopes:
    #   well-insulated radiator install: -1.0 to -1.4 (supply rises 1.0-1.4 K per 1 K outdoor drop)
    #   underfloor heating: -0.4 to -0.7
    if slope > -0.3:
        verdict = "very flat — increase the curve at the cold end"
    elif slope > -0.5:
        verdict = "flat — typical for underfloor heating"
    elif slope > -0.8:
        verdict = "moderate — typical for mixed underfloor / radiators"
    elif slope > -1.2:
        verdict = "steep — typical for radiator-only installs"
    elif slope > -1.5:
        verdict = "very steep — consider lowering or check insulation"
    else:
        verdict = "extremely steep — almost certainly over-tuned for cold weather"

    base = f"slope {slope:.2f} K/K, intercept {intercept:.1f} °C, R²={r2:.2f}, n={n}"
    return f"{verdict}. {base}."


def write_to_ha(base_url: str, token: str, entity: str, value: str) -> bool:
    url = f"{base_url}/api/services/input_text/set_value"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }, data=json.dumps({"entity_id": entity, "value": value[:255]}).encode("utf-8"))
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        print(f"failed to write {entity}: HTTP {e.code}", file=sys.stderr)
        return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--dry-run", action="store_true",
                   help="Print recommendation but don't write to HA")
    args = p.parse_args()

    base_url = os.environ.get("HA_BASE_URL", "http://homeassistant.local:8123").rstrip("/")
    token = os.environ.get("HA_TOKEN")
    if not token:
        print("HA_TOKEN environment variable required", file=sys.stderr)
        return 1

    start = datetime.now(timezone.utc) - timedelta(days=args.days)
    print(f"fetching {args.days} days of history from {base_url}")

    supply = fetch_history(base_url, token, "sensor.hph_source_outlet_temp", start)
    outdoor = fetch_history(base_url, token, "sensor.hph_source_outdoor_temp", start)
    compressor = fetch_history(base_url, token, "binary_sensor.hph_compressor_running", start)

    print(f"  supply: {len(supply)} points")
    print(f"  outdoor: {len(outdoor)} points")
    print(f"  compressor: {len(compressor)} state changes")

    pairs = align(supply, outdoor, compressor)
    print(f"  aligned compressor-on pairs: {len(pairs)}")

    slope, intercept, r2 = least_squares(pairs)
    rec = recommend(slope, intercept, r2, len(pairs))
    print(f"\nRecommendation: {rec}")

    if args.dry_run:
        return 0

    ok = write_to_ha(base_url, token,
                     "input_text.hph_heating_curve_recommendation", rec)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
