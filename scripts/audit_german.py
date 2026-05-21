#!/usr/bin/env python3
"""HeatPump Hero — autonomous German UI-string auditor.

Detects unintentional German display strings across all HPH source files and
(optionally) fixes them in-place.

Strategy
--------
"Intentional German" strings are loaded from the translation files that are
*supposed* to be German:
  - translations/de.json            (entity names — correct in German UI)
  - help_de.json                    (hph-tile/hph-help labels — correct)
  - hph-cards.js __HPH_HERO_I18N.de (hph-hero card labels — correct)

Everything else is scanned. A German string found OUTSIDE those sources is
classified as UNINTENTIONAL and reported as a FINDING.

Usage
-----
  py scripts/audit_german.py              # scan only, exit 0 = clean
  py scripts/audit_german.py --fix        # scan + auto-fix known strings
  py scripts/audit_german.py --live       # also check live HA entity states
  py scripts/audit_german.py --fix --live # both

Environment
-----------
  HA_BASE_URL   default http://192.168.111.2:8123
  HA_TOKEN      required for --live

Exit codes
----------
  0   clean — no unintentional German strings found (or all fixed by --fix)
  1   findings remain
  2   runtime error (missing file, bad JSON, etc.)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import NamedTuple

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parent.parent
CC = ROOT / "custom_components" / "hph"
DATA = CC / "data"

# ── Detection patterns ─────────────────────────────────────────────────────

UMLAUT_RE = re.compile(r"[äöüÄÖÜß]")
GERMAN_WORD_RE = re.compile(
    r"(?<![a-zA-Z_])("
    r"Heizen|Kühlen|Warmwasser|Heizung|Kühlung|Bereit|Betrieb|"
    r"Fehler|WMZ|veraltet|aktiv(?!ate)|bereit|Abtauung|Abtaudauer|Abtau(?![\w])|"
    r"Spreizung|Heizgrenze|Vorlauf|Rücklauf|Brauchwasser|"
    r"Laufzeit|Datenqualität|Raumtemperatur|"
    r"Thermisch\w*|Elektrisch\w*|Druck(?=\s)"
    r")(?![a-zA-Z_])",
    re.IGNORECASE,
)

# YAML keys that carry machine-readable values, not display strings.
_NON_DISPLAY_KEYS = frozenset(
    {
        "entity", "entity_id", "type", "platform", "icon", "service",
        "service_data", "data", "condition", "state", "state_not",
        "url", "path", "navigation_path", "action", "unique_id", "id",
        "device_class", "state_class", "unit_of_measurement", "availability",
        "value_template", "attribute", "source", "currency", "media_content_id",
        "target", "field", "event_type", "translation_key", "label_key",
        "object_id", "domain", "style", "card_mod", "layout_type", "mode",
        "resource", "columns", "color", "color_else", "color_entity",
        "icon_color", "suffix", "round", "decimals", "precision",
        "max_age", "sampling_size", "state_characteristic", "entity_id",
        "automation_id", "script_id", "blueprint_id",
    }
)

# ── Known translations (German → English) ─────────────────────────────────
# Used by --fix to auto-translate UNINTENTIONAL strings we already know about.

_KNOWN_TRANSLATIONS: dict[str, str] = {
    # hph_efficiency.yaml — core-platform sensor names (no translation_key support)
    "Heizgrenze (geglättet)": "Heating limit (smoothed)",
    "Spreizung 7-Tage-Mittel": "Spread 7-day mean",
    "Spreizung 7-Tage-Stdabw.": "Spread 7-day std dev",
    "Brauchwasser-Starts 7-Tage-Mittel": "DHW fires 7-day mean",
    "Druck 7-Tage-Mittel": "Pressure 7-day mean",
    "Raumtemperatur-Abweichung (geglättet)": "Room deviation (smoothed)",
    "Vorlauf − Außen (24 h)": "Supply − Outdoor (24 h)",
    "Datenqualität 24-h-Messwerte": "Data quality 24h samples",
    "Thermische Energie": "Thermal Energy",
    "Elektrische Energie": "Electrical Energy",
    "Thermische Energie (Laufzeit)": "Thermal Energy (runtime)",
    "Elektrische Energie (Laufzeit)": "Electrical Energy (runtime)",
    "Elektrische Energie Heizen (Laufzeit)": "Electrical Energy Heating (runtime)",
    "Elektrische Energie Brauchwasser (Laufzeit)": "Electrical Energy DHW (runtime)",
    "Elektrische Energie Kühlen (Laufzeit)": "Electrical Energy Cooling (runtime)",
    "Thermische Energie Brauchwasser (Laufzeit)": "Thermal Energy DHW (runtime)",
    "Abtauungen (24 h)": "Defrost cycles (24 h)",
    "Abtaudauer (24 h)": "Defrost duration (24 h)",
    # Dashboard Jinja template literals
    "WMZ veraltet": "Heat meter stale",
    "Strom veraltet": "Power stale",
    "Quellen veraltet": "Sources stale",
    "Kein aktiver Fehler": "No active error",
    "Fehler:": "Error:",
    "Modus:": "Mode:",
    "Ruhe:": "Quiet:",
    "Bereit": "Ready",
    "aktiv": "active",
    "bereit": "ready",
}


# ── Finding model ──────────────────────────────────────────────────────────

class Finding(NamedTuple):
    file: str       # relative path from repo root
    lineno: int
    key: str        # YAML key or JS context
    value: str      # the German string
    fixable: bool   # True = known translation exists


# ── Intentional-German loader ──────────────────────────────────────────────

def _load_intentional_german() -> frozenset[str]:
    """Return all German strings that are *correct* (from de.json, help_de.json,
    hph-cards.js __HPH_HERO_I18N.de)."""
    intentional: set[str] = set()

    # translations/de.json  — entity names
    de_json = CC / "translations" / "de.json"
    if de_json.is_file():
        data = json.loads(de_json.read_text(encoding="utf-8"))
        for platform_entries in (data.get("entity") or {}).values():
            for body in (platform_entries or {}).values():
                if isinstance(body, dict):
                    for v in body.values():
                        if isinstance(v, str):
                            intentional.add(v)

    # help_de.json  — hph-tile / hph-help labels
    help_de = DATA / "dashboards" / "assets" / "help_de.json"
    if help_de.is_file():
        data = json.loads(help_de.read_text(encoding="utf-8"))
        for entry in data.values():
            if isinstance(entry, dict):
                for v in entry.values():
                    if isinstance(v, str):
                        intentional.add(v)

    # hph-cards.js  — __HPH_HERO_I18N.de block
    js_file = DATA / "dashboards" / "assets" / "hph-cards.js"
    if js_file.is_file():
        js = js_file.read_text(encoding="utf-8")
        # Extract the `de: { ... }` block from __HPH_HERO_I18N
        m = re.search(r"__HPH_HERO_I18N\s*=\s*\{.*?de:\s*\{([^}]+)\}", js, re.DOTALL)
        if m:
            for s in re.findall(r'"([^"]+)"|\'([^\']+)\'', m.group(1)):
                intentional.add(s[0] or s[1])

    return frozenset(intentional)


# ── YAML scanner ──────────────────────────────────────────────────────────

def _is_german(s: str) -> bool:
    return bool(UMLAUT_RE.search(s) or GERMAN_WORD_RE.search(s))


def _scan_yaml_file(path: Path, intentional: frozenset[str]) -> list[Finding]:
    """Line-by-line scan of a YAML file for German display strings."""
    findings: list[Finding] = []
    rel = str(path.relative_to(ROOT))
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        print(f"  [WARN] cannot read {rel}: {e}")
        return findings

    # Regexes for display-value lines (key: value)
    value_re = re.compile(r"^(\s*)(\w[\w_-]*)\s*:\s*(.+)$")
    jinja_re = re.compile(r"\{\{|\{%")
    # String literals inside Jinja expressions
    jinja_str_re = re.compile(r"'([^']*)'")

    for lineno, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if jinja_re.search(raw):
            # Scan single-quoted string literals inside Jinja expressions
            for lit in jinja_str_re.findall(raw):
                if _is_german(lit) and lit not in intentional:
                    findings.append(Finding(
                        rel, lineno, "jinja-literal", lit,
                        lit in _KNOWN_TRANSLATIONS,
                    ))
            continue

        m = value_re.match(raw)
        if not m:
            continue
        key = m.group(2)
        val = m.group(3).strip().strip("\"'")

        if key.lower() in _NON_DISPLAY_KEYS:
            continue
        if jinja_re.search(val):
            continue
        if not _is_german(val):
            continue
        if val in intentional:
            continue

        findings.append(Finding(
            rel, lineno, key, val,
            val in _KNOWN_TRANSLATIONS,
        ))

    return findings


# ── JS scanner ────────────────────────────────────────────────────────────

def _scan_js_file(path: Path, intentional: frozenset[str]) -> list[Finding]:
    """Scan JS file for German strings outside the known i18n.de block."""
    findings: list[Finding] = []
    rel = str(path.relative_to(ROOT))
    try:
        js = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"  [WARN] cannot read {rel}: {e}")
        return findings

    # Remove the __HPH_HERO_I18N = { ... } block so .de: strings aren't flagged.
    js_stripped = re.sub(r"const __HPH_HERO_I18N\s*=\s*\{.*?\};", "", js, flags=re.DOTALL)
    # Also remove // comments
    js_stripped = re.sub(r"//[^\n]*", "", js_stripped)
    # Also remove /* */ comments
    js_stripped = re.sub(r"/\*.*?\*/", "", js_stripped, flags=re.DOTALL)

    for lineno, raw in enumerate(js_stripped.splitlines(), 1):
        stripped = raw.strip()
        if not stripped:
            continue
        # Find string literals
        for m in re.finditer(r'"([^"]+)"|\'([^\']+)\'', raw):
            lit = m.group(1) or m.group(2)
            if not _is_german(lit):
                continue
            if lit in intentional:
                continue
            findings.append(Finding(
                rel, lineno, "js-literal", lit,
                lit in _KNOWN_TRANSLATIONS,
            ))

    return findings


# ── Auto-fixer ────────────────────────────────────────────────────────────

def _apply_fixes(findings: list[Finding]) -> tuple[int, list[Finding]]:
    """Replace known German strings with English equivalents in-place.
    Returns (fixed_count, unfixable_findings)."""
    fixable = [f for f in findings if f.fixable]
    unfixable = [f for f in findings if not f.fixable]

    # Group fixable findings by file
    by_file: dict[str, list[Finding]] = {}
    for f in fixable:
        by_file.setdefault(f.file, []).append(f)

    fixed = 0
    for rel, file_findings in by_file.items():
        path = ROOT / rel
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"  [WARN] cannot read {rel} for fixing: {e}")
            unfixable.extend(file_findings)
            continue
        changed = False
        for finding in file_findings:
            eng = _KNOWN_TRANSLATIONS.get(finding.value)
            if eng and finding.value in content:
                content = content.replace(finding.value, eng)
                print(f"  [FIX ] {rel}:{finding.lineno}  {finding.value!r} → {eng!r}")
                fixed += 1
                changed = True
        if changed:
            path.write_text(content, encoding="utf-8")

    return fixed, unfixable


# ── Live HA check ─────────────────────────────────────────────────────────

def _check_live(base: str, token: str) -> list[Finding]:
    """Query live HA, check HPH entity state values + attributes for German."""
    findings: list[Finding] = []
    url = f"{base}/api/states"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            states = json.loads(resp.read())
    except Exception as e:  # noqa: BLE001
        print(f"  [WARN] cannot reach {base}/api/states: {e}")
        return findings

    hph_states = [s for s in states if ".hph_" in s.get("entity_id", "")]
    checked = 0
    for st in hph_states:
        eid = st["entity_id"]
        # Check state value
        state_val = st.get("state", "")
        if _is_german(state_val):
            findings.append(Finding(f"LIVE:{eid}", 0, "state", state_val, False))
        # Check attributes (except friendly_name — that follows HA language correctly)
        attrs = st.get("attributes", {})
        for attr_key, attr_val in attrs.items():
            if attr_key == "friendly_name":
                continue
            if isinstance(attr_val, str) and _is_german(attr_val):
                findings.append(Finding(
                    f"LIVE:{eid}", 0, f"attr.{attr_key}", attr_val, False,
                ))
        checked += 1

    print(f"  checked {checked} HPH entity state/attribute values")
    return findings


# ── Main ──────────────────────────────────────────────────────────────────

# Files/globs to scan
_YAML_TARGETS: list[Path] = [
    ROOT / "dashboards" / "hph.yaml",
    DATA / "packages" / "hph_efficiency.yaml",
    ROOT / "packages" / "hph_efficiency.yaml",
    DATA / "sensor_templates.yaml",
    DATA / "binary_sensor_templates.yaml",
]
# Also all packages/*.yaml in the repo root
_YAML_TARGETS += sorted((ROOT / "packages").glob("*.yaml"))
# Deduplicate (hph_efficiency.yaml appears twice above on purpose — both paths)
seen: set[Path] = set()
YAML_TARGETS: list[Path] = []
for p in _YAML_TARGETS:
    if p.is_file() and p not in seen:
        seen.add(p)
        YAML_TARGETS.append(p)

JS_TARGETS: list[Path] = [
    DATA / "dashboards" / "assets" / "hph-cards.js",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit HPH source files for unintentional German UI strings."
    )
    parser.add_argument("--fix", action="store_true",
                        help="Auto-translate known German strings in-place.")
    parser.add_argument("--live", action="store_true",
                        help="Also check live HA entity states (needs HA_TOKEN).")
    args = parser.parse_args()

    print("HeatPump Hero German-string audit")

    # Step 1: build intentional-German set
    intentional = _load_intentional_german()
    print(f"  intentional-German set: {len(intentional)} strings (from de.json, help_de.json, hph-cards.js)")

    all_findings: list[Finding] = []

    # Step 2: scan YAML files
    print(f"\n=== Static scan — {len(YAML_TARGETS)} YAML + {len(JS_TARGETS)} JS file(s) ===")
    for path in YAML_TARGETS:
        rel = path.relative_to(ROOT)
        found = _scan_yaml_file(path, intentional)
        if found:
            print(f"  {rel}: {len(found)} finding(s)")
            all_findings.extend(found)
        else:
            print(f"  {rel}: clean")

    # Step 3: scan JS files
    for path in JS_TARGETS:
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        found = _scan_js_file(path, intentional)
        if found:
            print(f"  {rel}: {len(found)} finding(s)")
            all_findings.extend(found)
        else:
            print(f"  {rel}: clean")

    # Step 4: live check (optional)
    if args.live:
        print("\n=== Live HA entity state check ===")
        base = os.environ.get("HA_BASE_URL", "http://192.168.111.2:8123").rstrip("/")
        token = os.environ.get("HA_TOKEN")
        if not token:
            print("  [WARN] HA_TOKEN not set — skipping live check")
        else:
            live_findings = _check_live(base, token)
            if live_findings:
                print(f"  {len(live_findings)} live finding(s)")
                all_findings.extend(live_findings)
            else:
                print("  no German entity state values found")

    # Step 5: auto-fix (optional)
    unfixable = all_findings
    if args.fix and all_findings:
        print(f"\n=== Auto-fix — {len([f for f in all_findings if f.fixable])} fixable ===")
        fixed, unfixable = _apply_fixes(all_findings)
        if fixed:
            print(f"  fixed {fixed} string(s)")

    # Report
    print()
    if not unfixable:
        if not all_findings:
            print(f"RESULT: clean — 0 unintentional German strings found")
        else:
            print(f"RESULT: all {len(all_findings)} finding(s) fixed")
        return 0

    fixable_count = sum(1 for f in unfixable if f.fixable)
    review_count = sum(1 for f in unfixable if not f.fixable)
    print(f"RESULT: {len(unfixable)} finding(s) remain "
          f"({fixable_count} fixable with --fix, {review_count} need manual review)")
    for f in unfixable[:40]:
        tag = "[FIX?]" if f.fixable else "[REVIEW]"
        print(f"  {tag} {f.file}:{f.lineno}  {f.key}: {f.value!r}")
    if len(unfixable) > 40:
        print(f"  ... and {len(unfixable) - 40} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
