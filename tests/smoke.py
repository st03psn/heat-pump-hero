#!/usr/bin/env python3
"""
Heat Pump Hero — local smoke tests.

Validates structural invariants without booting a real HA instance:

  1. All package YAML, dashboard YAML, blueprint YAML load cleanly.
  2. All Grafana JSON files load cleanly.
  3. The source-adapter contract holds: no hardcoded `panasonic_heat_pump_*`
     references outside the packages where they belong (sources.yaml as
     defaults, control.yaml as documented heat-pump-specific write targets,
     dashboard heat-curve auto-entities filter, dashboard main on/off switch).
  4. All `sensor.hph_source_*` references in core/advisor/cycles/
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
DASHBOARD_FILE = ROOT / "dashboards" / "hph.yaml"
BLUEPRINT_FILE = ROOT / "blueprints" / "hph_setup.yaml"

# Files allowed to contain hardcoded heat-pump entity references.
ALLOWED_HARDCODE = {
    "packages/hph_sources.yaml": "default values for the source-adapter helpers",
    "packages/hph_control.yaml": "heat-pump-specific write targets (documented)",
    "packages/hph_models.yaml": "vendor-preset auto-fill payloads (write per-vendor entity-IDs into helpers)",
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
        if rel == "dashboards/hph.yaml":
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
    section("Source-facade resolution — every hph_source_* must be defined")
    failures = 0

    # Facade sensors can be defined in any HPH package (hph_sources is the
    # primary, but hph_analysis adds indoor temp facades, etc.)
    facade_names: set[str] = set()
    for pkg in (ROOT / "packages").glob("hph_*.yaml"):
        d = load_yaml(pkg)
        for block in d.get("template", []) or []:
            for sensor in block.get("sensor", []) or []:
                facade_names.add(sensor["unique_id"])
            for sensor in block.get("binary_sensor", []) or []:
                facade_names.add(sensor["unique_id"])

    if not facade_names:
        fail("no template facades found — refactor regression?")
        return 1

    ok(f"all packages define {len(facade_names)} facade entities")

    # Look for sensor.hph_source_* references everywhere except the
    # packages that define them (they reference themselves naturally)
    facade_ref_pattern = re.compile(
        r"(?:sensor|binary_sensor)\.hph_source_(\w+)"
    )
    others = list(PACKAGE_FILES) + [DASHBOARD_FILE]

    used: set[str] = set()
    for f in others:
        text = f.read_text(encoding="utf-8")
        for m in facade_ref_pattern.findall(text):
            used.add(m)

    if not used:
        ok("(no facade references in other files — empty install?)")
    else:
        ok(f"facade entities referenced from other files: {len(used)}")

    # Map back: every used unique_id should match a `hph_source_<x>` definition
    missing = []
    for u in used:
        if f"hph_source_{u}" not in facade_names:
            missing.append(u)

    if missing:
        for m in missing:
            fail(f"sensor.hph_source_{m} is referenced but not defined in sources.yaml")
        failures += len(missing)
    else:
        ok("all referenced facade entities are defined")

    return failures


# ─── Test 4: utility_meter sources point to the _active variants ────────────
def test_utility_meter_active_source() -> int:
    section("utility_meter sources go through *_active dispatchers")
    failures = 0

    eff = load_yaml(ROOT / "packages" / "hph_efficiency.yaml")
    counters = eff.get("utility_meter", {}) or {}

    # Sources are either `_active` energy sensors or other utility_meters; allow both.
    for name, cfg in counters.items():
        src = cfg.get("source", "")
        if src in (
            "sensor.hph_thermal_energy_active",
            "sensor.hph_electrical_energy_active",
        ):
            ok(f"{name} -> {src}")
        else:
            fail(f"{name} sources from {src} — expected an *_active dispatcher")
            failures += 1

    return failures


# ─── Test 5: every advisor that summary aggregates is actually defined ───
def test_advisor_summary_consistency() -> int:
    section("Advisor summary aggregates only sensors that exist")
    failures = 0

    # Advisors can live in multiple packages — scan all of them.
    advisor_text = ""
    for pkg in (ROOT / "packages").glob("hph_*.yaml"):
        advisor_text += pkg.read_text(encoding="utf-8") + "\n"
    text = advisor_text

    declared = set(re.findall(r"unique_id:\s*(hph_advisor_\w+)", text))

    # Find advisor entities the summary reads
    summary_block_match = re.search(
        r"unique_id:\s*hph_advisor_summary.*?attributes:",
        text,
        flags=re.S,
    )
    if not summary_block_match:
        fail("advisor summary block not found")
        return 1

    summary_block = text[summary_block_match.start():summary_block_match.end()]
    referenced = set(re.findall(r"sensor\.(hph_advisor_\w+)", summary_block))
    referenced.discard("hph_advisor_summary")

    missing = referenced - declared
    if missing:
        for m in missing:
            fail(f"advisor summary references {m} which is not defined in advisor.yaml")
        failures += len(missing)
    else:
        ok(f"advisor summary aggregates {len(referenced)} declared advisors")

    return failures


# ─── Test 6: diagnostics package self-consistency ────────────────────────
def test_diagnostics_consistency() -> int:
    section("Diagnostics module self-consistency")
    failures = 0

    diag = load_yaml(ROOT / "packages" / "hph_diagnostics.yaml")

    # Find the current_error template sensor
    current_error_def = None
    for block in diag.get("template", []):
        for s in block.get("sensor", []) or []:
            if s.get("unique_id") == "hph_diagnostics_current_error":
                current_error_def = s
                break

    if not current_error_def:
        fail("hph_diagnostics_current_error not declared")
        return 1
    ok("hph_diagnostics_current_error declared")

    # Severity arrays should reference codes that appear in the message
    state_text = str(current_error_def.get("attributes", {}).get("severity", ""))
    msg_text = str(current_error_def.get("attributes", {}).get("message", ""))

    # Extract severity arrays
    sev_codes = set(re.findall(r"['\"]([HF]\d{2})['\"]", state_text))
    msg_codes = set(re.findall(r"== '([HF]\d{2})'", msg_text))

    missing_in_msg = sev_codes - msg_codes
    # H00 is mapped to 'ok' so it doesn't need a per-code branch
    missing_in_msg.discard("H00")
    if missing_in_msg:
        for m in sorted(missing_in_msg):
            fail(f"severity lists {m} but no message branch handles it")
        failures += len(missing_in_msg)
    else:
        ok(f"all {len(sev_codes)} codes in severity lists have message branches")

    return failures


def main() -> int:
    print(f"Heat Pump Hero smoke tests · root: {ROOT}")
    failures = 0
    failures += test_files_parse()
    failures += test_source_adapter_contract()
    failures += test_source_facade_resolution()
    failures += test_utility_meter_active_source()
    failures += test_advisor_summary_consistency()
    failures += test_diagnostics_consistency()

    print()
    if failures:
        print(f"FAILED: {failures} failure(s).")
        return 1
    print("PASSED: all smoke tests green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
