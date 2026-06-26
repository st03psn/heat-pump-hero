"""Tests for efficiency template sensors.

Two tiers:
  - Pure-Python simulation tests (always run, no HA required).
  - HA-based template tests (skipped when pytest-homeassistant-custom-component
    is absent; render actual Jinja expressions from sensor_templates.yaml).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_HA_AVAILABLE = importlib.util.find_spec("pytest_homeassistant_custom_component") is not None
_skip_without_ha = pytest.mark.skipif(not _HA_AVAILABLE, reason="pytest-homeassistant-custom-component not installed")

if _HA_AVAILABLE:
    from homeassistant.core import HomeAssistant  # noqa: E402
    from homeassistant.helpers.template import Template  # noqa: E402

_TEMPLATES = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "hph"
    / "data"
    / "sensor_templates.yaml"
)


# ---------------------------------------------------------------------------
# Helpers for HA template tests
# ---------------------------------------------------------------------------

def _state_expr(unique_id: str) -> str:
    import yaml
    sensors = yaml.safe_load(_TEMPLATES.read_text(encoding="utf-8"))
    for entry in sensors:
        if entry.get("unique_id") == unique_id:
            return entry["state"]
    raise AssertionError(f"unique_id {unique_id!r} not found in {_TEMPLATES}")


def _render(hass, unique_id: str) -> str:
    return Template(_state_expr(unique_id), hass).async_render()


def _attr_expr(unique_id: str, attr: str) -> str:
    import yaml
    sensors = yaml.safe_load(_TEMPLATES.read_text(encoding="utf-8"))
    for entry in sensors:
        if entry.get("unique_id") == unique_id:
            return entry["attributes"][attr]
    raise AssertionError(f"unique_id {unique_id!r} not found in {_TEMPLATES}")


# ---------------------------------------------------------------------------
# HA-based template tests
# ---------------------------------------------------------------------------

@_skip_without_ha
async def test_hph_scop_excludes_cooling(hass) -> None:
    """With a cooling pot present, both numerator and denominator drop it."""
    hass.states.async_set("sensor.hph_thermal_yearly", "1000")
    hass.states.async_set("sensor.hph_electrical_yearly", "300")
    hass.states.async_set("sensor.hph_thermal_yearly_split_cooling", "100")
    hass.states.async_set("sensor.hph_electrical_yearly_split_cooling", "50")
    await hass.async_block_till_done()
    assert float(_render(hass, "hph_scop")) == 3.6


@_skip_without_ha
async def test_hph_scop_unknown_cooling_matches_legacy(hass) -> None:
    hass.states.async_set("sensor.hph_thermal_yearly", "1000")
    hass.states.async_set("sensor.hph_electrical_yearly", "300")
    hass.states.async_set("sensor.hph_thermal_yearly_split_cooling", "unknown")
    hass.states.async_set("sensor.hph_electrical_yearly_split_cooling", "unknown")
    await hass.async_block_till_done()
    assert float(_render(hass, "hph_scop")) == 3.33


@_skip_without_ha
async def test_hph_scop_zero_cooling_matches_legacy(hass) -> None:
    hass.states.async_set("sensor.hph_thermal_yearly", "1000")
    hass.states.async_set("sensor.hph_electrical_yearly", "300")
    hass.states.async_set("sensor.hph_thermal_yearly_split_cooling", "0")
    hass.states.async_set("sensor.hph_electrical_yearly_split_cooling", "0")
    await hass.async_block_till_done()
    assert float(_render(hass, "hph_scop")) == 3.33


@_skip_without_ha
async def test_hph_cop_daily_excludes_cooling(hass) -> None:
    hass.states.async_set("sensor.hph_thermal_daily", "40")
    hass.states.async_set("sensor.hph_electrical_daily", "12")
    hass.states.async_set("sensor.hph_thermal_daily_split_cooling", "4")
    hass.states.async_set("sensor.hph_electrical_daily_split_cooling", "2")
    await hass.async_block_till_done()
    assert float(_render(hass, "hph_cop_daily")) == 3.6


@_skip_without_ha
async def test_thermal_power_cooling_magnitude(hass) -> None:
    hass.states.async_set("sensor.hph_operating_mode", "cooling")
    hass.states.async_set("sensor.hph_source_inlet_temp", "18")
    hass.states.async_set("sensor.hph_source_outlet_temp", "12")
    hass.states.async_set("sensor.hph_source_flow_rate", "20")
    await hass.async_block_till_done()
    assert float(_render(hass, "hph_thermal_power_cooling")) == 8358


@_skip_without_ha
async def test_thermal_power_cooling_zero_when_not_cooling(hass) -> None:
    hass.states.async_set("sensor.hph_operating_mode", "heating")
    hass.states.async_set("sensor.hph_source_inlet_temp", "30")
    hass.states.async_set("sensor.hph_source_outlet_temp", "35")
    hass.states.async_set("sensor.hph_source_flow_rate", "20")
    await hass.async_block_till_done()
    assert float(_render(hass, "hph_thermal_power_cooling")) == 0


@_skip_without_ha
async def test_seer_from_cooling_meters(hass) -> None:
    hass.states.async_set("sensor.hph_thermal_cooling_runtime_yearly", "200")
    hass.states.async_set("sensor.hph_electrical_cooling_runtime_yearly", "50")
    await hass.async_block_till_done()
    assert float(_render(hass, "hph_seer")) == 4.0


@_skip_without_ha
async def test_eer_live_from_power(hass) -> None:
    hass.states.async_set("sensor.hph_thermal_power_cooling", "3000")
    hass.states.async_set("sensor.hph_electrical_power_cooling_runtime", "1000")
    await hass.async_block_till_done()
    assert float(_render(hass, "hph_eer_live")) == 3.0


@_skip_without_ha
async def test_efficiency_live_heating_shows_cop(hass) -> None:
    hass.states.async_set("sensor.hph_operating_mode", "heating")
    hass.states.async_set("sensor.hph_cop_live", "4.2")
    hass.states.async_set("sensor.hph_eer_live", "0")
    await hass.async_block_till_done()
    assert float(_render(hass, "hph_efficiency_live")) == 4.2
    assert Template(_attr_expr("hph_efficiency_live", "metric"), hass).async_render() == "COP"


@_skip_without_ha
async def test_efficiency_live_cooling_shows_eer(hass) -> None:
    hass.states.async_set("sensor.hph_operating_mode", "cooling")
    hass.states.async_set("sensor.hph_cop_live", "0")
    hass.states.async_set("sensor.hph_eer_live", "3.4")
    await hass.async_block_till_done()
    value = float(_render(hass, "hph_efficiency_live"))
    assert value == 3.4
    assert value >= 0
    assert Template(_attr_expr("hph_efficiency_live", "metric"), hass).async_render() == "EER"


@_skip_without_ha
async def test_efficiency_seasonal_swaps_scop_seer(hass) -> None:
    hass.states.async_set("sensor.hph_scop", "3.8")
    hass.states.async_set("sensor.hph_seer", "5.1")
    hass.states.async_set("sensor.hph_operating_mode", "heating")
    await hass.async_block_till_done()
    assert float(_render(hass, "hph_efficiency_seasonal")) == 3.8
    assert Template(_attr_expr("hph_efficiency_seasonal", "metric"), hass).async_render() == "SCOP"
    hass.states.async_set("sensor.hph_operating_mode", "cooling")
    await hass.async_block_till_done()
    assert float(_render(hass, "hph_efficiency_seasonal")) == 5.1
    assert Template(_attr_expr("hph_efficiency_seasonal", "metric"), hass).async_render() == "SEER"


# ---------------------------------------------------------------------------
# Pure-Python simulation tests (always run, no HA required)
# ---------------------------------------------------------------------------

def _cop_live(thermal_w: float, electrical_w: float, defrost: bool, compressor: bool) -> float:
    if defrost or not compressor:
        return 0.0
    return round(thermal_w / electrical_w, 2) if electrical_w > 150 else 0.0


def _eer_live_sim(thermal_w: float, electrical_w: float, mode: str, compressor: bool) -> float:
    if mode != "cooling" or not compressor:
        return 0.0
    t = abs(thermal_w)
    return round(t / electrical_w, 2) if electrical_w > 150 else 0.0


def _efficiency_live_sim(cop: float, eer: float, mode: str):
    if mode == "cooling":
        return eer, "EER"
    return cop, "COP"


def _thermal_power_display_sim(thermal_w: float) -> float:
    return abs(thermal_w)


def _eer_stat(thermal_kwh: float, electrical_kwh: float, threshold: float = 0.1) -> float:
    return round(thermal_kwh / electrical_kwh, 2) if electrical_kwh > threshold else 0.0


def _pv_coverage(solar_kwh: float, export_kwh: float, hp_kwh: float) -> float:
    self_consumed = max(solar_kwh - export_kwh, 0.0)
    if hp_kwh <= 0:
        return 0.0
    return min(max(round(self_consumed / hp_kwh * 100, 1), 0.0), 100.0)


class TestEfficiencyLive:
    def test_heating_mode_returns_cop(self):
        cop = _cop_live(5000, 1000, defrost=False, compressor=True)
        eer = _eer_live_sim(5000, 1000, mode="heating", compressor=True)
        value, metric = _efficiency_live_sim(cop, eer, mode="heating")
        assert metric == "COP"
        assert value == cop

    def test_cooling_mode_returns_eer(self):
        cop = _cop_live(-4900, 1200, defrost=False, compressor=True)
        eer = _eer_live_sim(-4900, 1200, mode="cooling", compressor=True)
        value, metric = _efficiency_live_sim(cop, eer, mode="cooling")
        assert metric == "EER"
        assert value == eer
        assert value >= 0

    def test_dhw_mode_returns_cop(self):
        cop = _cop_live(3000, 900, defrost=False, compressor=True)
        eer = _eer_live_sim(3000, 900, mode="dhw", compressor=True)
        _, metric = _efficiency_live_sim(cop, eer, mode="dhw")
        assert metric == "COP"

    def test_standby_returns_zero(self):
        cop = _cop_live(0, 0, defrost=False, compressor=False)
        eer = _eer_live_sim(0, 0, mode="heating", compressor=False)
        value, _ = _efficiency_live_sim(cop, eer, mode="heating")
        assert value == 0.0


class TestEerLiveSim:
    def test_cooling_positive(self):
        result = _eer_live_sim(-4900, 1200, mode="cooling", compressor=True)
        assert result == round(4900 / 1200, 2)
        assert result >= 0

    def test_heating_zero(self):
        assert _eer_live_sim(5000, 1000, mode="heating", compressor=True) == 0.0

    def test_compressor_off_zero(self):
        assert _eer_live_sim(-4900, 1200, mode="cooling", compressor=False) == 0.0

    def test_low_power_zero(self):
        assert _eer_live_sim(-2000, 100, mode="cooling", compressor=True) == 0.0


class TestThermalPowerDisplay:
    def test_cooling_positive(self):
        assert _thermal_power_display_sim(-4900) == 4900

    def test_heating_unchanged(self):
        assert _thermal_power_display_sim(5000) == 5000

    def test_zero(self):
        assert _thermal_power_display_sim(0) == 0


class TestEerStats:
    def test_eer_daily_normal(self):
        assert _eer_stat(10.0, 3.0, threshold=0.1) == round(10.0 / 3.0, 2)

    def test_zero_electrical(self):
        assert _eer_stat(5.0, 0.0) == 0.0

    def test_below_threshold(self):
        assert _eer_stat(5.0, 0.05) == 0.0

    def test_monthly_threshold(self):
        assert _eer_stat(5.0, 0.3, threshold=0.5) == 0.0
        assert _eer_stat(5.0, 0.6, threshold=0.5) == round(5.0 / 0.6, 2)

    def test_yearly_threshold(self):
        assert _eer_stat(50.0, 0.9, threshold=1.0) == 0.0
        assert _eer_stat(50.0, 1.1, threshold=1.0) == round(50.0 / 1.1, 2)


class TestPvCoverage:
    def test_normal(self):
        assert _pv_coverage(solar_kwh=5.0, export_kwh=2.0, hp_kwh=4.0) == 75.0

    def test_hp_zero(self):
        assert _pv_coverage(solar_kwh=5.0, export_kwh=2.0, hp_kwh=0.0) == 0.0

    def test_cap_100(self):
        assert _pv_coverage(solar_kwh=20.0, export_kwh=0.0, hp_kwh=5.0) == 100.0

    def test_export_exceeds_production(self):
        assert _pv_coverage(solar_kwh=2.0, export_kwh=5.0, hp_kwh=4.0) == 0.0

    def test_rounding(self):
        assert _pv_coverage(solar_kwh=3.0, export_kwh=1.0, hp_kwh=6.0) == 33.3
