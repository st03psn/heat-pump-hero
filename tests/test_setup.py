"""Integration setup tests — entity creation and vendor preset application.

These tests run against a real hass instance (no manual HA UI required).
They require pytest-homeassistant-custom-component and are skipped when
that package is not installed (e.g. local dev without a full HA env).
"""

from __future__ import annotations

import importlib.util
from types import MappingProxyType
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("pytest_homeassistant_custom_component") is None,
    reason="pytest-homeassistant-custom-component not installed",
)

from homeassistant.core import HomeAssistant  # noqa: E402  (conditional import)

from custom_components.hph.const import (
    CTRL_FACADES,
    DOMAIN,
    MODEL_CAPABILITIES,
    TEXT_HELPERS,
    VENDOR_PRESETS,
    _MODEL_CONDITIONAL,
)

# Minimal config-entry data that passes the setup guard.
_BASE_ENTRY_DATA = {
    "vendor_preset": "keep_current",
    "pump_model": "panasonic_l_aql",
}


async def _setup_entry(hass: HomeAssistant, data: dict | None = None) -> None:
    """Create and set up an HPH config entry with the given data."""
    from homeassistant.config_entries import ConfigEntryState

    entry_data = {**_BASE_ENTRY_DATA, **(data or {})}
    entry = hass.config_entries.async_entries(DOMAIN)
    if entry:
        return  # already loaded

    # Bootstrap is I/O-heavy; skip file operations in unit tests.
    with (
        patch(
            "custom_components.hph.bootstrap.async_deploy_yaml_packages",
            return_value={
                "migrated_removed": [],
                "stale_cleaned": [],
                "efficiency": True,
                "ext_thermal_redirected": False,
                "ext_electrical_redirected": False,
            },
        ),
        patch("custom_components.hph.bootstrap.async_register_dashboard"),
        patch(
            "custom_components.hph.__init__._async_check_prerequisites",
        ),
    ):
        from homeassistant.config_entries import ConfigEntry

        entry = ConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="HeatPump Hero",
            data=entry_data,
            options={},
            source="user",
            unique_id=None,
            discovery_keys=MappingProxyType({}),
        )
        await hass.config_entries.async_add(entry)
        await hass.async_block_till_done()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_setup_creates_all_text_helpers(hass: HomeAssistant) -> None:
    """Every key in TEXT_HELPERS must exist as a text.* entity after setup."""
    await _setup_entry(hass)

    missing = []
    for uid in TEXT_HELPERS:
        entity_id = f"text.{uid}"
        if hass.states.get(entity_id) is None:
            missing.append(entity_id)

    assert not missing, (
        f"{len(missing)} text helper(s) not created after setup:\n"
        + "\n".join(f"  {e}" for e in sorted(missing))
    )


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_vendor_preset_panasonic_l_gates_fan2(hass: HomeAssistant) -> None:
    """L-series: fan1_speed fills, fan2_speed stays empty (single-fan unit)."""
    await _setup_entry(hass, {
        "vendor_preset": "panasonic_heishamon",
        "pump_model": "panasonic_l_aql",
    })

    fan1 = hass.states.get("text.hph_src_fan1_speed")
    fan2 = hass.states.get("text.hph_src_fan2_speed")

    assert fan1 is not None, "text.hph_src_fan1_speed missing"
    assert fan2 is not None, "text.hph_src_fan2_speed missing"

    assert fan1.state != "", (
        "L-series should have fan1_speed filled by preset; got empty"
    )
    assert fan2.state == "", (
        f"L-series has only one fan — fan2_speed must be empty, got {fan2.state!r}"
    )


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_vendor_preset_panasonic_j_gates_fan2(hass: HomeAssistant) -> None:
    """J-series: fan2_speed stays empty (single-fan unit). pump_pressure is
    universal across J/K/L/T-CAP/M and must be filled."""
    await _setup_entry(hass, {
        "vendor_preset": "panasonic_heishamon",
        "pump_model": "panasonic_j_aqj",
    })

    fan2 = hass.states.get("text.hph_src_fan2_speed")
    pump_pressure = hass.states.get("text.hph_src_pump_pressure")

    assert fan2 is not None
    assert fan2.state == "", (
        f"J-series: fan2_speed must be empty, got {fan2.state!r}"
    )
    assert pump_pressure is not None
    assert pump_pressure.state != "", (
        f"pump_pressure must be filled (universal across Panasonic models), got {pump_pressure.state!r}"
    )


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_vendor_preset_panasonic_tcap_fills_fan2(hass: HomeAssistant) -> None:
    """T-CAP: fan2_speed must be filled (dual-fan unit)."""
    await _setup_entry(hass, {
        "vendor_preset": "panasonic_heishamon",
        "pump_model": "panasonic_tcap",
    })

    fan2 = hass.states.get("text.hph_src_fan2_speed")
    assert fan2 is not None
    assert fan2.state != "", (
        "T-CAP is a dual-fan unit — fan2_speed must be filled by preset"
    )


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_vendor_preset_panasonic_m_fills_fan2(hass: HomeAssistant) -> None:
    """M-series: fan2_speed must be filled (dual-fan unit)."""
    await _setup_entry(hass, {
        "vendor_preset": "panasonic_heishamon",
        "pump_model": "panasonic_m_aqm",
    })

    fan2 = hass.states.get("text.hph_src_fan2_speed")
    assert fan2 is not None
    assert fan2.state != "", (
        "M-series is a dual-fan unit — fan2_speed must be filled by preset"
    )


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_model_capabilities_cover_all_preset_src_keys() -> None:
    """MODEL_CAPABILITIES sets must cover every hph_src_* key in the Panasonic preset.

    If a new src helper is added to VENDOR_PRESETS without updating
    MODEL_CAPABILITIES, that sensor would silently appear on all models.
    This test catches that omission.
    """
    panasonic_src_keys = {
        k.removeprefix("hph_src_")
        for k in VENDOR_PRESETS["panasonic_heishamon"]
        if k.startswith("hph_src_")
    }
    # internal_thermal_power is intentionally NOT in MODEL_CAPABILITIES
    # (it has a non-empty default and is present on all models).
    # _MODEL_CONDITIONAL keys (e.g. fan2_speed) are gated per-model by a
    # dedicated mechanism — models without the feature legitimately omit
    # them from MODEL_CAPABILITIES, so they must not be flagged here.
    always_present = {"internal_thermal_power"} | set(_MODEL_CONDITIONAL)

    for model_key, caps in MODEL_CAPABILITIES.items():
        if not model_key.startswith("panasonic_"):
            continue
        ungated = panasonic_src_keys - caps - always_present
        # Ungated sensors that are in the preset but not in caps will fill on all models.
        # That's only acceptable for "always_present" ones.
        assert not ungated, (
            f"Model {model_key}: sensors in Panasonic preset but not in "
            f"MODEL_CAPABILITIES (will fill unconditionally): {ungated!r}. "
            "Add them to MODEL_CAPABILITIES or to always_present."
        )


def test_ctrl_facades_writers_exist_in_text_helpers() -> None:
    """Every CTRL_FACADES.writer must reference a real TEXT_HELPERS entry."""
    missing = [
        (uid, cfg["writer"])
        for uid, cfg in CTRL_FACADES.items()
        if cfg["writer"] not in TEXT_HELPERS
    ]
    assert not missing, (
        f"{len(missing)} CTRL_FACADES entries reference unknown writer helpers: {missing!r}"
    )


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_setup_creates_all_facade_proxies(hass: HomeAssistant) -> None:
    """Every CTRL_FACADES entry must result in a registered proxy entity."""
    await _setup_entry(hass)

    missing = []
    for uid, cfg in CTRL_FACADES.items():
        domain = cfg["platform"]
        entity_id = f"{domain}.{uid}"
        if hass.states.get(entity_id) is None:
            missing.append(entity_id)

    assert not missing, (
        f"{len(missing)} facade proxy entity/entities not created after setup:\n"
        + "\n".join(f"  {e}" for e in sorted(missing))
    )
