#!/usr/bin/env python3
"""HeatPump Hero — configure external energy source helpers via HA REST API.

Sets the Shelly 3EM and Sensostar WMZ entities as the external energy/power
sources and switches both source-mode selectors to `external_energy`. Also
reloads the HPH config entry so bootstrap rewrites hph_efficiency.yaml with
the Sensostar/Shelly entities as direct utility_meter sources.

Usage:
    # Dry-run (show what would be set):
    HA_TOKEN=eyJh... python scripts/configure_sources.py

    # Apply:
    HA_TOKEN=eyJh... python scripts/configure_sources.py --confirm

Environment:
    HA_TOKEN       long-lived access token (mandatory for --confirm)
    HA_BASE_URL    e.g. http://192.168.111.73:8123 (default)
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HA_BASE = os.environ.get("HA_BASE_URL", "http://192.168.111.73:8123").rstrip("/")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

# Ground-truth sensor entity IDs
SHELLY_ENERGY  = "sensor.3em_wpaussen_total_active_energy"
SHELLY_POWER   = "sensor.3em_wpaussen_total_active_power"
SENSOSTAR_ENERGY = "sensor.sensostar_9ce898_sensostar_energy"
SENSOSTAR_POWER  = "sensor.sensostar_9ce898_sensostar_calculated_power"

# Helper changes: list of (service_path, payload)
CHANGES = [
    ("input_text/set_value",   {"entity_id": "input_text.hph_src_external_thermal_energy",   "value": SENSOSTAR_ENERGY}),
    ("input_text/set_value",   {"entity_id": "input_text.hph_src_external_thermal_power",    "value": SENSOSTAR_POWER}),
    ("input_text/set_value",   {"entity_id": "input_text.hph_src_external_electrical_energy","value": SHELLY_ENERGY}),
    ("input_text/set_value",   {"entity_id": "input_text.hph_src_external_electrical_power", "value": SHELLY_POWER}),
    ("input_select/select_option", {"entity_id": "input_select.hph_thermal_source",    "option": "external_energy"}),
    ("input_select/select_option", {"entity_id": "input_select.hph_electrical_source", "option": "external_energy"}),
]

HPH_DOMAIN = "hph"


def _headers() -> dict:
    return {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}


def _post(path: str, data: dict) -> dict:
    url = f"{HA_BASE}{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=_headers())
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _get(path: str) -> dict | list:
    url = f"{HA_BASE}{path}"
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _current_state(entity_id: str) -> str:
    try:
        return _get(f"/api/states/{entity_id}")["state"]
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description="Configure HPH external source helpers")
    ap.add_argument("--confirm", action="store_true",
                    help="Actually write to HA (default: dry-run preview only)")
    args = ap.parse_args()

    if args.confirm and not HA_TOKEN:
        print("ERROR: HA_TOKEN required for --confirm mode", file=sys.stderr)
        return 1

    print(f"\nHPH Source Configuration -- {'LIVE' if args.confirm else 'DRY RUN (add --confirm to apply)'}")
    print(f"HA: {HA_BASE}\n")

    print("-- Helper changes -----------------------------------------------")
    for service, payload in CHANGES:
        entity = payload.get("entity_id", "")
        new_val = payload.get("value") or payload.get("option", "")
        current = _current_state(entity) if HA_TOKEN else "?"
        status = "same" if current == new_val else "CHANGE"
        print(f"  {entity}")
        print(f"    current : {current}")
        print(f"    -> set  : {new_val}  [{status}]")
        if args.confirm:
            try:
                _post(f"/api/services/{service}", payload)
                print(f"    -> OK")
            except Exception as exc:
                print(f"    -> ERROR: {exc}", file=sys.stderr)
        print()

    if args.confirm:
        print("-- Reloading HPH integration (triggers bootstrap rewrite) -------")
        try:
            entries = _get("/api/config/config_entries/entry")
            hph_entry = next((e for e in entries if e.get("domain") == HPH_DOMAIN), None)
            if hph_entry:
                entry_id = hph_entry["entry_id"]
                print(f"  Entry ID : {entry_id}")
                _post("/api/services/homeassistant/reload_config_entry", {"entry_id": entry_id})
                print("  -> Reload triggered — bootstrap will rewrite hph_efficiency.yaml")
                print("     (utility_meter source lines now point to Sensostar/Shelly directly)")
            else:
                print("  HPH config entry not found — reload manually: Settings -> Integrations -> HPH -> Reload")
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
        print()

    if not args.confirm:
        print("Dry-run complete. Run with --confirm to apply.\n")
        print("Note: --confirm also reloads the HPH integration which triggers")
        print("bootstrap to rewrite packages/hph_efficiency.yaml with the external")
        print("meter entities as direct utility_meter sources (avoids gaps on reload).")
    else:
        print("Done. COP should now reflect Sensostar/Shelly values within ~1 minute.")
        print("Verify with:  python scripts/check_plausibility.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
