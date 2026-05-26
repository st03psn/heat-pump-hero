#!/usr/bin/env python3
"""
HeatPump Hero — migrate utility_meter mode tariffs (v0.9 → v0.10 layout).

Background:
    The split utility_meters (hph_thermal_yearly_split, hph_electrical_yearly_split,
    and the daily/monthly siblings) gained a fourth tariff 'standby' alongside
    the existing 'heating', 'dhw', 'cooling'. Existing heating/dhw/cooling
    tariff values should survive the reload. If HA decides to reset them
    when the tariff list changes, this script restores them via
    utility_meter.calibrate.

Workflow:
    1. BEFORE updating the HPH integration on the target HA instance, run:
           python3 migrate_mode_tariffs.py --host <ha-host> --snapshot
       This writes scripts/migration_backup_<host>_<ts>.json with the
       current per-tariff totals via REST.
    2. Update the integration (HACS or manual copy).
    3. Reload HPH in HA (Developer Tools → YAML → Reload Custom Integrations,
       or reload via the Integration config).
    4. Verify post-state matches snapshot:
           python3 migrate_mode_tariffs.py --host <ha-host> --verify \\
               --snapshot scripts/migration_backup_<host>_<ts>.json
       If all diffs are ~0, nothing to do.
    5. If any value drifted (HA reset a tariff), restore:
           python3 migrate_mode_tariffs.py --host <ha-host> --apply \\
               --snapshot scripts/migration_backup_<host>_<ts>.json
       Idempotent — safe to re-run.

Environment:
    HA_BASE_URL (or --host with implicit http://<host>:8123)
    HA_TOKEN    (long-lived access token, required)

The script writes ONLY via REST/WebSocket — no direct DB access.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# Split utility_meter parents — each one fans out into <parent>_<tariff>
# sensors. The 4 tariffs follow.
SPLIT_PARENTS = [
    "sensor.hph_thermal_daily_split",
    "sensor.hph_electrical_daily_split",
    "sensor.hph_thermal_monthly_split",
    "sensor.hph_electrical_monthly_split",
    "sensor.hph_thermal_yearly_split",
    "sensor.hph_electrical_yearly_split",
]
TARIFFS = ["heating", "dhw", "cooling", "standby"]


def _http(method: str, url: str, token: str, payload: dict | None = None) -> dict | list | None:
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body.strip() else None
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code} for {url}: {exc.read().decode('utf-8', 'ignore')}", file=sys.stderr)
        raise


def fetch_state(base: str, token: str, entity_id: str) -> str | None:
    try:
        data = _http("GET", f"{base}/api/states/{entity_id}", token)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    if not isinstance(data, dict):
        return None
    return data.get("state")


def collect_snapshot(base: str, token: str) -> dict:
    snap = {"taken_at": datetime.utcnow().isoformat() + "Z", "host": base, "tariffs": {}}
    for parent in SPLIT_PARENTS:
        for tariff in TARIFFS:
            ent = f"{parent}_{tariff}"
            state = fetch_state(base, token, ent)
            try:
                value = float(state) if state not in (None, "unknown", "unavailable", "") else None
            except ValueError:
                value = None
            snap["tariffs"][ent] = value
    return snap


def calibrate(base: str, token: str, entity_id: str, value: float, dry_run: bool) -> bool:
    payload = {"entity_id": entity_id, "value": str(value)}
    if dry_run:
        print(f"  [dry-run] would calibrate {entity_id} → {value}")
        return True
    try:
        _http("POST", f"{base}/api/services/utility_meter/calibrate", token, payload)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  calibrate {entity_id} failed: {exc}", file=sys.stderr)
        return False


def cmd_snapshot(args, base: str, token: str) -> int:
    snap = collect_snapshot(base, token)
    host_slug = urllib.parse.urlparse(base).netloc.replace(":", "_") or "ha"
    ts = time.strftime("%Y%m%dT%H%M%S")
    out = args.out or f"scripts/migration_backup_{host_slug}_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2)
    populated = sum(1 for v in snap["tariffs"].values() if v is not None)
    print(f"snapshot written → {out}")
    print(f"  {populated}/{len(snap['tariffs'])} tariff entities populated")
    return 0


def cmd_verify(args, base: str, token: str) -> int:
    with open(args.snapshot, encoding="utf-8") as f:
        snap = json.load(f)
    current = collect_snapshot(base, token)
    drift = 0
    for ent, want in snap["tariffs"].items():
        have = current["tariffs"].get(ent)
        if want is None and have is None:
            continue
        if want is None or have is None:
            print(f"  CHANGED {ent}: snapshot={want} now={have}")
            drift += 1
            continue
        if abs(have - want) > 0.01:
            print(f"  DRIFT   {ent}: snapshot={want:.3f} now={have:.3f} (Δ={have - want:+.3f})")
            drift += 1
    print(f"verify: {drift} differences vs. snapshot")
    return 0 if drift == 0 else 2


def cmd_apply(args, base: str, token: str) -> int:
    with open(args.snapshot, encoding="utf-8") as f:
        snap = json.load(f)
    current = collect_snapshot(base, token)
    restored = 0
    skipped = 0
    for ent, want in snap["tariffs"].items():
        if want is None:
            skipped += 1
            continue
        have = current["tariffs"].get(ent)
        if have is not None and abs(have - want) <= 0.01:
            skipped += 1
            continue
        print(f"  restoring {ent}: {have} → {want}")
        if calibrate(base, token, ent, want, dry_run=args.dry_run):
            restored += 1
    print(f"apply: {restored} calibrated, {skipped} unchanged")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", help="HA base URL (default: $HA_BASE_URL or http://homeassistant.local:8123)")
    p.add_argument("--token", help="HA long-lived token (default: $HA_TOKEN)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", action="store_true", help="Take a snapshot of current tariff totals")
    g.add_argument("--verify", metavar="FILE", help="Compare current state against snapshot FILE")
    g.add_argument("--apply", metavar="FILE", help="Restore values from snapshot FILE via utility_meter.calibrate")
    p.add_argument("--out", help="Output path for --snapshot (default: auto-named under scripts/)")
    p.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = p.parse_args()

    base = (args.host or os.environ.get("HA_BASE_URL") or "http://homeassistant.local:8123").rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = f"http://{base}:8123"
    token = args.token or os.environ.get("HA_TOKEN")
    if not token:
        print("HA_TOKEN environment variable (or --token) required", file=sys.stderr)
        return 1

    if args.verify:
        args.snapshot = args.verify
        return cmd_verify(args, base, token)
    if args.apply:
        args.snapshot = args.apply
        return cmd_apply(args, base, token)
    return cmd_snapshot(args, base, token)


if __name__ == "__main__":
    sys.exit(main())
