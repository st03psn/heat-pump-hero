"""Dashboard YAML structural tests — catch unsupported Lovelace features.

These tests parse the dashboard YAML without starting HA, so they're
fast enough to run as pre-commit checks in addition to CI.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

DASHBOARD_PATH = (
    Path(__file__).parent.parent
    / "custom_components" / "hph" / "data" / "dashboards" / "hph.yaml"
)

# Load const.py directly — bypasses __init__.py (which imports homeassistant).
_HPH_DIR = Path(__file__).parent.parent / "custom_components" / "hph"


def _load_const_standalone() -> ModuleType:
    name = "_hph_const_for_dashboard_tests"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _HPH_DIR / "const.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_const = _load_const_standalone()


@pytest.fixture(scope="module")
def dashboard() -> dict[str, Any]:
    return yaml.safe_load(DASHBOARD_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _walk_cards(obj: Any):
    """Recursively yield every card dict from a Lovelace YAML structure."""
    if isinstance(obj, dict):
        if "type" in obj:
            yield obj
        for v in obj.values():
            yield from _walk_cards(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_cards(item)


def _walk_conditions(obj: Any):
    """Yield every condition dict from conditional cards."""
    if isinstance(obj, dict):
        if "conditions" in obj:
            for cond in obj["conditions"]:
                if isinstance(cond, dict):
                    yield cond
        for v in obj.values():
            yield from _walk_conditions(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_conditions(item)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_dashboard_yaml_parses(dashboard) -> None:
    """Dashboard YAML must parse without errors."""
    assert isinstance(dashboard, dict)
    assert "views" in dashboard


def test_no_condition_template_in_dashboard(dashboard) -> None:
    """condition: template is NOT supported by Lovelace conditional cards.

    Regression: the Control tab previously used condition: template which
    caused "Konfigurationsfehler" red cards in the UI.
    Supported types: state, numeric_state, screen, user, time, and, or, not.
    """
    bad_conditions = []
    for cond in _walk_conditions(dashboard):
        if cond.get("condition") == "template":
            bad_conditions.append(cond)

    assert not bad_conditions, (
        f"Found {len(bad_conditions)} unsupported 'condition: template' entries "
        f"in dashboard.yaml. Use 'condition: state' instead:\n"
        + "\n".join(f"  {c}" for c in bad_conditions)
    )


def test_no_local_hph_asset_urls(dashboard) -> None:
    """Dashboard must not reference /local/hph/ URLs (stale pre-rc5 path).

    Since rc5, SVGs are served via /hph_assets/ directly from the
    integration data directory; no copy to <config>/www/hph/ is made.
    """
    raw = DASHBOARD_PATH.read_text(encoding="utf-8")
    matches = re.findall(r"/local/hph/\S+\.svg", raw)
    assert not matches, (
        f"Found stale /local/hph/*.svg URLs in dashboard.yaml — "
        f"replace with /hph_assets/: {matches}"
    )


def test_machine_room_tiles_are_conditional(dashboard) -> None:
    """Every Machine Room sensor tile must be wrapped in a conditional card.

    Tiles for sensors that may not exist on all models (fan2, pressures, etc.)
    must hide when the corresponding text.hph_src_* helper is empty.
    """
    _MUST_BE_CONDITIONAL = {
        "text.hph_src_fan2_speed",
        "text.hph_src_fan1_speed",
        "text.hph_src_inverter_temp",
        "text.hph_src_high_pressure",
        "text.hph_src_low_pressure",
        "text.hph_src_compressor_current",
        "text.hph_src_outdoor_pipe_temp",
        "text.hph_src_3way_valve",
        "text.hph_src_pump_duty",
        "text.hph_src_hex_outlet_temp",
        "text.hph_src_zone1_target_temp",
    }

    # Collect all conditional card guard entities
    guarded: set[str] = set()
    for card in _walk_cards(dashboard):
        if card.get("type") == "conditional":
            for cond in card.get("conditions", []):
                if "entity" in cond:
                    guarded.add(cond["entity"])

    missing_guards = _MUST_BE_CONDITIONAL - guarded
    assert not missing_guards, (
        f"Machine Room tiles missing conditional guard:\n"
        + "\n".join(f"  {e}" for e in sorted(missing_guards))
    )


def test_conditional_helper_entities_exist_in_const(dashboard) -> None:
    """Every entity used in a conditional card guard must be a known HPH helper.

    Guards referencing non-existent helpers would make tiles always-hidden.
    """
    known = {f"text.{uid}" for uid in _const.TEXT_HELPERS}

    unknown_guards = []
    for cond in _walk_conditions(dashboard):
        entity = cond.get("entity", "")
        if entity.startswith("text.hph_") and entity not in known:
            unknown_guards.append(entity)

    assert not unknown_guards, (
        f"Conditional card guards reference unknown text helpers:\n"
        + "\n".join(f"  {e}" for e in sorted(set(unknown_guards)))
    )
