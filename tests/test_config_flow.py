"""Config flow tests — vendor filtering, stale key regression.

Part A (test_const_*): imports only const.py via importlib.
Runs without HA installed — no homeassistant dependency.

Part B (test_flow_*): imports config_flow.py which needs homeassistant.
Skipped when the package is absent (CI installs it via requirements_test.txt).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

# ---------------------------------------------------------------------------
# Load const.py directly — bypasses custom_components/hph/__init__.py which
# imports homeassistant. const.py only uses stdlib (pathlib, typing).
# ---------------------------------------------------------------------------
_HPH_DIR = Path(__file__).parent.parent / "custom_components" / "hph"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"Cannot find {path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_const = _load_module("_hph_const_standalone", _HPH_DIR / "const.py")
PUMP_MODELS = _const.PUMP_MODELS
VENDOR_MODELS = _const.VENDOR_MODELS

_HA_AVAILABLE = importlib.util.find_spec("homeassistant") is not None

# ---------------------------------------------------------------------------
# Part A — pure const.py tests (no HA required)
# ---------------------------------------------------------------------------

def test_const_vendor_models_all_keys_exist_in_pump_models() -> None:
    """Every model key referenced in VENDOR_MODELS must exist in PUMP_MODELS."""
    for vendor, models in VENDOR_MODELS.items():
        for model_key in models:
            assert model_key in PUMP_MODELS, (
                f"VENDOR_MODELS[{vendor!r}] references unknown model {model_key!r}"
            )


def test_const_panasonic_vendors_only_show_panasonic_models() -> None:
    """Both Panasonic preset keys must restrict to Panasonic-only models."""
    for vendor_key in ("panasonic_heishamon", "panasonic_heishamon_aquarea"):
        allowed = set(VENDOR_MODELS[vendor_key])
        non_panasonic = {k for k in PUMP_MODELS if not k.startswith("panasonic_")}
        leaked = allowed & non_panasonic
        assert not leaked, (
            f"VENDOR_MODELS[{vendor_key!r}] contains non-Panasonic models: {leaked}"
        )


def test_const_both_panasonic_presets_same_model_list() -> None:
    """panasonic_heishamon and panasonic_heishamon_aquarea must offer the same models."""
    assert set(VENDOR_MODELS["panasonic_heishamon"]) == set(
        VENDOR_MODELS["panasonic_heishamon_aquarea"]
    )


def test_const_keep_current_includes_all_models() -> None:
    """keep_current must include all PUMP_MODELS (power-user fallback)."""
    keep = set(VENDOR_MODELS.get("keep_current", []))
    all_keys = set(PUMP_MODELS.keys())
    assert all_keys.issubset(keep), f"keep_current missing: {all_keys - keep}"


def test_const_model_capabilities_keys_are_panasonic() -> None:
    """MODEL_CAPABILITIES should only contain Panasonic model keys."""
    for model_key in _const.MODEL_CAPABILITIES:
        assert model_key in PUMP_MODELS, (
            f"MODEL_CAPABILITIES has key {model_key!r} not in PUMP_MODELS"
        )


def test_const_l_series_has_no_fan2_capability() -> None:
    """L-series is a single-fan unit — fan2_speed must not be in its capabilities."""
    caps = _const.MODEL_CAPABILITIES.get("panasonic_l_aql", set())
    assert "fan2_speed" not in caps, (
        "panasonic_l_aql should not have fan2_speed (single-fan unit, confirmed)"
    )


def test_const_j_series_has_no_fan2_capability() -> None:
    """J-series is a single-fan unit — fan2_speed must not be in its capabilities."""
    caps = _const.MODEL_CAPABILITIES.get("panasonic_j_aqj", set())
    assert "fan2_speed" not in caps


def test_const_tcap_has_fan2_capability() -> None:
    """T-CAP is a dual-fan unit — fan2_speed must be in its capabilities."""
    caps = _const.MODEL_CAPABILITIES.get("panasonic_tcap", set())
    assert "fan2_speed" in caps, (
        "panasonic_tcap should have fan2_speed (dual-fan T-CAP unit)"
    )


def test_const_m_series_has_fan2_capability() -> None:
    """M-series is a dual-fan unit — fan2_speed must be in its capabilities."""
    caps = _const.MODEL_CAPABILITIES.get("panasonic_m_aqm", set())
    assert "fan2_speed" in caps


# ---------------------------------------------------------------------------
# Part B — config_flow.py tests (require homeassistant)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HA_AVAILABLE, reason="homeassistant not installed")
def test_flow_aquarea_preset_selectable() -> None:
    """Regression: panasonic_heishamon_aquarea must be in selectable keys.

    Previous bug: _selectable_vendor_keys() had 'panasonic_heishamon_mqtt'
    making the aquarea preset unreachable from the config flow UI.
    """
    from custom_components.hph.config_flow import _selectable_vendor_keys

    selectable = _selectable_vendor_keys()
    assert "panasonic_heishamon_aquarea" in selectable, (
        "panasonic_heishamon_aquarea not in selectable vendors — "
        "check for stale 'panasonic_heishamon_mqtt' entry"
    )
    assert "panasonic_heishamon_mqtt" not in selectable, (
        "panasonic_heishamon_mqtt is a stale key and must not be selectable"
    )


@pytest.mark.skipif(not _HA_AVAILABLE, reason="homeassistant not installed")
def test_flow_model_dropdown_filtered_by_panasonic_heishamon() -> None:
    """Selecting a Panasonic vendor must restrict models to Panasonic only."""
    from custom_components.hph.config_flow import _model_options

    options = _model_options("panasonic_heishamon")
    values = {opt["value"] for opt in options}

    panasonic_keys = set(VENDOR_MODELS["panasonic_heishamon"])
    non_panasonic_keys = set(PUMP_MODELS.keys()) - panasonic_keys

    assert values == panasonic_keys
    assert not (values & non_panasonic_keys)


@pytest.mark.skipif(not _HA_AVAILABLE, reason="homeassistant not installed")
def test_flow_model_dropdown_unknown_vendor_shows_all() -> None:
    """An unknown vendor key must fall back to all models (no KeyError)."""
    from custom_components.hph.config_flow import _model_options

    options = _model_options("vendor_that_does_not_exist")
    values = {opt["value"] for opt in options}
    all_keys = set(PUMP_MODELS.keys())
    assert all_keys.issubset(values)
