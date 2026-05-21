#!/usr/bin/env python3
"""HeatPump Hero — runtime i18n / frontend verification against a live HA.

Proves, without any manual clicking, that:

  1. Entity NAMES resolve through the translation files (German on a German
     instance) — i.e. the rc9 ``_attr_name`` removal took effect. Reads the
     real ``friendly_name`` from ``/api/states`` and compares it against the
     expected German name built from ``translations/de.json``.
  2. The ``hph-help`` custom card asset is served (``/hph_assets/hph-help.js``
     → HTTP 200). A 404 means the static path is broken; 200 means a
     "Konfigurationsfehler" is a browser/Service-Worker cache issue, not code.
  3. The frontend module mount logged success (``/api/error_log``).

Config via env:

  HA_BASE_URL   default http://192.168.111.2:8123 (test instance)
  HA_TOKEN      long-lived access token (REQUIRED — never hardcode/commit it)

Auth/REST pattern mirrors scripts/export_heishahub.py.

Exit code 0 = entity names verified German; 1 = mismatches found.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:  # Windows consoles default to cp1252 — force UTF-8 so umlauts print.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parent.parent
DE_JSON = ROOT / "custom_components" / "hph" / "translations" / "de.json"

# Test instance default base. The token must come from the HA_TOKEN env var —
# never hardcode a long-lived token here (it would leak into git history).
DEFAULT_BASE = "http://192.168.111.2:8123"

DEVICE_PREFIX = "HeatPump Hero "


def _get(base: str, token: str, path: str, raw: bool = False):
    url = f"{base}{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
        if raw:
            return resp.status, body.decode("utf-8", "replace")
        return resp.status, json.loads(body)


def _expected_names() -> dict[tuple[str, str], str]:
    """(platform, uid) -> German entity name from de.json."""
    data = json.loads(DE_JSON.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], str] = {}
    for platform, entries in (data.get("entity") or {}).items():
        for uid, body in (entries or {}).items():
            name = (body or {}).get("name")
            if name:
                out[(platform, uid)] = name
    return out


def check_entity_names(base: str, token: str) -> int:
    print("\n=== 1. Entity names (friendly_name via /api/states) ===")
    expected = _expected_names()
    try:
        status, states = _get(base, token, "/api/states")
    except urllib.error.URLError as e:
        print(f"  [FAIL] cannot reach {base}/api/states: {e}")
        return 1

    by_entity_id = {s["entity_id"]: s for s in states}

    checked = 0
    english = []  # friendly_name does not end with the German name
    missing = 0   # entity not present on this install (optional hardware etc.)

    for (platform, uid), de_name in sorted(expected.items()):
        entity_id = f"{platform}.{uid}"
        st = by_entity_id.get(entity_id)
        if st is None:
            missing += 1
            continue
        checked += 1
        friendly = st.get("attributes", {}).get("friendly_name", "")
        # has_entity_name=True → "HeatPump Hero <name>". Accept either the
        # prefixed or bare form; the suffix is what matters.
        if not friendly.endswith(de_name):
            english.append((entity_id, friendly, f"{DEVICE_PREFIX}{de_name}"))

    print(f"  present: {checked}   not-on-this-install: {missing}   "
          f"(de.json defines {len(expected)})")

    if english:
        print(f"  [FAIL] {len(english)} entities NOT showing the German name:")
        for entity_id, got, exp in english[:60]:
            print(f"         {entity_id}\n             got:      {got!r}\n"
                  f"             expected: ...{exp!r}")
        if len(english) > 60:
            print(f"         ... and {len(english) - 60} more")
        return 1

    print(f"  [ OK ] all {checked} present hph entities show their German name")
    return 0


def check_help_asset(base: str, token: str) -> None:
    print("\n=== 2. hph-cards custom card asset ===")
    # File was renamed hph-help.js → hph-cards.js when the tile/hero cards
    # were added alongside hph-help (commit 98a8460).
    try:
        status, body = _get(base, token, "/hph_assets/hph-cards.js", raw=True)
        defines = "customElements.define(\"hph-help\"" in body or \
                  "customElements.define('hph-help'" in body
        print(f"  HTTP {status}, {len(body)} bytes, defines hph-help: {defines}")
        if status == 200 and defines:
            print("  [ OK ] asset served -> 'Konfigurationsfehler' is a browser "
                  "cache issue (hard-reload / clear Service Worker), not code")
        else:
            print("  [WARN] asset reachable but unexpected content")
    except urllib.error.HTTPError as e:
        print(f"  [FAIL] HTTP {e.code} for /hph_assets/hph-cards.js — static path "
              "not registered or integration not reloaded after rename")
    except urllib.error.URLError as e:
        print(f"  [FAIL] cannot reach asset: {e}")


def check_error_log(base: str, token: str) -> None:
    print("\n=== 3. Frontend module mount (/api/error_log) ===")
    try:
        status, log = _get(base, token, "/api/error_log", raw=True)
    except urllib.error.URLError as e:
        print(f"  [WARN] cannot read error log: {e}")
        return
    hits = [ln for ln in log.splitlines()
            if "HPH frontend module" in ln or "HPH assets" in ln]
    if not hits:
        print("  [info] no HPH frontend log lines (log may have rotated)")
    for ln in hits[-10:]:
        tag = "[ OK ]" if "mounted" in ln else "[WARN]"
        print(f"  {tag} {ln.strip()}")


def main() -> int:
    base = os.environ.get("HA_BASE_URL", DEFAULT_BASE).rstrip("/")
    token = os.environ.get("HA_TOKEN")
    if not token:
        print("  [FAIL] set HA_TOKEN env var (long-lived access token)")
        return 2
    print(f"HeatPump Hero i18n runtime verify · {base}")

    if not DE_JSON.is_file():
        print(f"  [FAIL] {DE_JSON} not found")
        return 1

    rc = check_entity_names(base, token)
    check_help_asset(base, token)
    check_error_log(base, token)

    print()
    print("RESULT:", "names verified German" if rc == 0 else "name mismatches found")
    return rc


if __name__ == "__main__":
    sys.exit(main())
