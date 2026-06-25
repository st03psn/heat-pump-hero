"""Logic tests for the COP/SCOP efficiency template sensors.

These render the *actual* `state:` Jinja expressions shipped in
`custom_components/hph/data/sensor_templates.yaml` against a real hass
template engine, so the assertions stay in sync with the deployed logic
(no copy of the expression lives in the test).

Focus: the cooling-exclusion fix. The plant-wide SCOP/COP figures
subtract the `…_split_cooling` tariff pot from both numerator and
denominator so cooling electricity no longer depresses the heating/DHW
JAZ. The `float(0)` fallback must make the subtraction a no-op while no
cooling data exists (identical to the pre-fix behaviour).

Requires pytest-homeassistant-custom-component (spins up an in-process
HA instance); skipped when that package is absent, exactly like
test_setup.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("pytest_homeassistant_custom_component") is None,
    reason="pytest-homeassistant-custom-component not installed",
)

from homeassistant.core import HomeAssistant  # noqa: E402  (conditional import)
from homeassistant.helpers.template import Template  # noqa: E402

_TEMPLATES = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "hph"
    / "data"
    / "sensor_templates.yaml"
)


def _state_expr(unique_id: str) -> str:
    """Return the raw `state:` Jinja for the sensor with this unique_id."""
    sensors = yaml.safe_load(_TEMPLATES.read_text(encoding="utf-8"))["sensors"]
    for entry in sensors:
        if entry.get("unique_id") == unique_id:
            return entry["state"]
    raise AssertionError(f"unique_id {unique_id!r} not found in {_TEMPLATES}")


def _render(hass: HomeAssistant, unique_id: str) -> str:
    return Template(_state_expr(unique_id), hass).async_render()


async def test_hph_scop_excludes_cooling(hass: HomeAssistant) -> None:
    """With a cooling pot present, both numerator and denominator drop it."""
    hass.states.async_set("sensor.hph_thermal_yearly", "1000")
    hass.states.async_set("sensor.hph_electrical_yearly", "300")
    hass.states.async_set("sensor.hph_thermal_yearly_split_cooling", "100")
    hass.states.async_set("sensor.hph_electrical_yearly_split_cooling", "50")
    await hass.async_block_till_done()

    # (1000-100)/(300-50) = 3.6 — NOT the raw 1000/300 ≈ 3.33.
    assert float(_render(hass, "hph_scop")) == 3.6


async def test_hph_scop_unknown_cooling_matches_legacy(hass: HomeAssistant) -> None:
    """An `unknown` cooling pot must reproduce the pre-fix value exactly."""
    hass.states.async_set("sensor.hph_thermal_yearly", "1000")
    hass.states.async_set("sensor.hph_electrical_yearly", "300")
    hass.states.async_set("sensor.hph_thermal_yearly_split_cooling", "unknown")
    hass.states.async_set("sensor.hph_electrical_yearly_split_cooling", "unknown")
    await hass.async_block_till_done()

    # float(0) fallback → 1000/300 = 3.33, identical to legacy behaviour.
    assert float(_render(hass, "hph_scop")) == 3.33


async def test_hph_scop_zero_cooling_matches_legacy(hass: HomeAssistant) -> None:
    """A literal 0 cooling pot is a no-op as well."""
    hass.states.async_set("sensor.hph_thermal_yearly", "1000")
    hass.states.async_set("sensor.hph_electrical_yearly", "300")
    hass.states.async_set("sensor.hph_thermal_yearly_split_cooling", "0")
    hass.states.async_set("sensor.hph_electrical_yearly_split_cooling", "0")
    await hass.async_block_till_done()

    assert float(_render(hass, "hph_scop")) == 3.33


async def test_hph_cop_daily_excludes_cooling(hass: HomeAssistant) -> None:
    """The `_daily` path uses the daily split pot — same subtraction shape."""
    hass.states.async_set("sensor.hph_thermal_daily", "40")
    hass.states.async_set("sensor.hph_electrical_daily", "12")
    hass.states.async_set("sensor.hph_thermal_daily_split_cooling", "4")
    hass.states.async_set("sensor.hph_electrical_daily_split_cooling", "2")
    await hass.async_block_till_done()

    # (40-4)/(12-2) = 3.6.
    assert float(_render(hass, "hph_cop_daily")) == 3.6


# ── EER / SEER (cooling-mode efficiency) ────────────────────────────────


async def test_thermal_power_cooling_magnitude(hass: HomeAssistant) -> None:
    """In cooling mode the sensor reports the POSITIVE heat-removed magnitude."""
    hass.states.async_set("sensor.hph_operating_mode", "cooling")
    hass.states.async_set("sensor.hph_source_inlet_temp", "18")
    hass.states.async_set("sensor.hph_source_outlet_temp", "12")
    hass.states.async_set("sensor.hph_source_flow_rate", "20")
    await hass.async_block_till_done()

    # tmean=15 → cp=4179; (18-12)*20*4179/60 = 8358 W (positive, not clamped 0).
    assert float(_render(hass, "hph_thermal_power_cooling")) == 8358


async def test_thermal_power_cooling_zero_when_not_cooling(hass: HomeAssistant) -> None:
    """Outside cooling mode the cooling magnitude is gated to 0."""
    hass.states.async_set("sensor.hph_operating_mode", "heating")
    hass.states.async_set("sensor.hph_source_inlet_temp", "30")
    hass.states.async_set("sensor.hph_source_outlet_temp", "35")
    hass.states.async_set("sensor.hph_source_flow_rate", "20")
    await hass.async_block_till_done()

    assert float(_render(hass, "hph_thermal_power_cooling")) == 0


async def test_seer_from_cooling_meters(hass: HomeAssistant) -> None:
    """SEER = seasonal cooling thermal / cooling electrical (positive ratio)."""
    hass.states.async_set("sensor.hph_thermal_cooling_runtime_yearly", "200")
    hass.states.async_set("sensor.hph_electrical_cooling_runtime_yearly", "50")
    await hass.async_block_till_done()

    # 200 / 50 = 4.0.
    assert float(_render(hass, "hph_seer")) == 4.0


async def test_eer_live_from_power(hass: HomeAssistant) -> None:
    """Live EER divides the cooling thermal power by the cooling electrical power."""
    hass.states.async_set("sensor.hph_thermal_power_cooling", "3000")
    hass.states.async_set("sensor.hph_electrical_power_cooling_runtime", "1000")
    await hass.async_block_till_done()

    # 3000 / 1000 = 3.0 (denominator above the 50 W floor).
    assert float(_render(hass, "hph_eer_live")) == 3.0
