#!/usr/bin/env python3
"""
HeishaHub — local smoke tests.

Validates structural invariants without booting a real HA instance:

  1. All package YAML, dashboard YAML, blueprint YAML load cleanly.
  2. All Grafana JSON files load cleanly.
  3. The source-adapter contract holds: no hardcoded `panasonic_heat_pump_*`
     references outside the packages where they belong (sources.yaml as
     defaults, control.yaml as documented heat-pump-specific write targets,
     dashboard heat-curve auto-entities filter, dashboard main on/off switch).
  4. All `sensor.heishahub_source_*` references in core/advisor/cycles/
     dashboards correspond to a sensor actually defined in sources.yaml.

Run:  py tests/smoke.py
Exit code 0 = all green, 1 = at least one failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

PACKAGE_FILES = sorted((ROOT / "packages").glob("*.yaml"))
GRAFANA_FILES = sorted((ROOT / "grafana").glob("*.json"))
DASHBOARD_FILE = ROOT / "dashboards" / "heishahub.yaml"
BLUEPRINT_FILE = ROOT / "blueprints" / "heishahub_setup.yaml"

# Files allowed to contain hardcoded heat-pump entity references.
ALLOWED_HARDCODE = {
    "packages/heishahub_sources.yaml": "default values for the source-adapter helpers",
    "packages/heishahub_control.yaml": "heat-pump-specific write targets (documented)",
}

# Dashboard exceptions: the main on/off switch and heat-curve auto-entities
# filters are heat-pump specific by nature and documented as such.
DASHBOARD_ALLOWED_PATTERNS = [
    r"switch\.panasonic_heat_pump_main_heatpump_state",
    r"number\.panasonic_heat_pump_main_z[12]_heat_curve_\*",
]


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def ok(msg: str) -> None:
    print(f"  [ OK ] {msg}")


def section(name: str) -> None:
    print(f"\n=== {name} ===")


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ─── Test 1: every YAML/JSON file parses ────────────────────────────────────
def test_files_parse() -> int:
    section("File-parse smoke")
    failures = 0

    for f in PACKAGE_FILES + [DASHBOARD_FILE, BLUEPRINT_FILE]:
        try:
            load_yaml(f)
            ok(f"YAML parses: {f.relative_to(ROOT)}")
        except Exception as e:
            fail(f"YAML broken: {f.relative_to(ROOT)}: {e}")
            failures += 1

    for f in GRAFANA_FILES:
        try:
            load_json(f)
            ok(f"JSON parses: {f.relative_to(ROOT)}")
        except Exception as e:
            fail(f"JSON broken: {f.relative_to(ROOT)}: {e}")
            failures += 1

    return failures


# ─── Test 2: source-adapter contract ────────────────────────────────────────
def test_source_adapter_contract() -> int:
    section("Source-adapter contract — no stray heat-pump refs")
    failures = 0
    pattern = re.compile(r"panasonic_heat_pump_\w+")

    for f in PACKAGE_FILES + [DASHBOARD_FILE]:
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        text = f.read_text(encoding="utf-8")

        # Strip allowed dashboard patterns before counting
        if rel == "dashboards/heishahub.yaml":
            for allowed in DASHBOARD_ALLOWED_PATTERNS:
                text = re.sub(allowed, "", text)

        hits = pattern.findall(text)
        if rel in ALLOWED_HARDCODE:
            ok(f"{rel}: {len(hits)} hardcoded refs (allowed: {ALLOWED_HARDCODE[rel]})")
        elif hits:
            fail(f"{rel}: {len(hits)} stray hardcoded refs — example: {hits[0]}")
            failures += 1
        else:
            ok(f"{rel}: clean (uses source facade)")

    return failures


# ─── Test 3: source-facade sensors used elsewhere all exist in sources.yaml ─
def test_source_facade_resolution() -> int:
    section("Source-facade resolution — every heishahub_source_* must be defined")
    failures = 0

    # Collect facade definitions from sources.yaml
    sources = load_yaml(ROOT / "packages" / "heishahub_sources.yaml")
    facade_names: set[str] = set()
    for block in sources.get("template", []):
        for sensor in block.get("sensor", []) or []:
            facade_names.add(sensor["unique_id"])
        for sensor in block.get("binary_sensor", []) or []:
            facade_names.add(sensor["unique_id"])

    if not facade_names:
        fail("sources.yaml exposes no template sensors — refactor regression?")
        return 1

    ok(f"sources.yaml defines {len(facade_names)} facade entities")

    # Look for sensor.heishahub_source_* references everywhere except sources itself
    facade_ref_pattern = re.compile(
        r"(?:sensor|binary_sensor)\.heishahub_source_(\w+)"
    )
    others = [f for f in PACKAGE_FILES if f.name != "heishahub_sources.yaml"]
    others.append(DASHBOARD_FILE)

    used: set[str] = set()
    for f in others:
        text = f.read_text(encoding="utf-8")
        for m in facade_ref_pattern.findall(text):
            used.add(m)

    if not used:
        ok("(no facade references in other files — empty install?)")
    else:
        ok(f"facade entities referenced from other files: {len(used)}")

    # Map back: every used unique_id should match a `heishahub_source_<x>` definition
    missing = []
    for u in used:
        if f"heishahub_source_{u}" not in facade_names:
            missing.append(u)

    if missing:
        for m in missing:
            fail(f"sensor.heishahub_source_{m} is referenced but not defined in sources.yaml")
        failures += len(missing)
    else:
        ok("all referenced facade entities are defined")

    return failures


# ─── Test 4: utility_meter sources point to the _active variants ────────────
def test_utility_meter_active_source() -> int:
    section("utility_meter sources go through *_active dispatchers")
    failures = 0

    eff = load_yaml(ROOT / "packages" / "heishahub_efficiency.yaml")
    counters = eff.get("utility_meter", {}) or {}

    # Sources are either `_active` energy sensors or other utility_meters; allow both.
    for name, cfg in counters.items():
        src = cfg.get("source", "")
        if src in (
            "sensor.heishahub_thermal_energy_active",
            "sensor.heishahub_electrical_energy_active",
        ):
            ok(f"{name} -> {src}")
        else:
            fail(f"{name} sources from {src} — expected an *_active dispatcher")
            failures += 1

    return failures


def main() -> int:
    print(f"HeishaHub smoke tests · root: {ROOT}")
    failures = 0
    failures += test_files_parse()
    failures += test_source_adapter_contract()
    failures += test_source_facade_resolution()
    failures += test_utility_meter_active_source()

    print()
    if failures:
        print(f"FAILED: {failures} failure(s).")
        return 1
    print("PASSED: all smoke tests green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
