"""HeatPump Hero — runtime-kWh coordinator (Stage B of standby fix).

Stage A redirected utility_meter daily/monthly/yearly totals to the
external energy meter directly so they survive HPH integration reloads.
Stage B (this file) does the same for the *runtime-only* kWh number used
by the standby breakdown.

Approach
--------
We track the user's external energy meter (Shelly / IoTaWatt / hardware
heat meter) as the ground truth and accumulate kWh **only during
compressor-on intervals** by sampling the meter at each transition:

  off → on : record `_baseline = current external meter value`
  on → off : add `(current − _baseline)` to the today accumulator
  midnight : reset accumulator; if compressor is currently on, also
             reset the baseline to "now" so the next interval boundary
             gets a clean reading

Outputs to:
  - `number.hph_thermal_runtime_today_kwh`     (RestoreEntity in number.py)
  - `number.hph_electrical_runtime_today_kwh`

Why Number entities and not new template sensors:
  - The accumulator must survive HA restarts (RestoreEntity)
  - We need to *write* to it from this coordinator (Number entities expose
    `number.set_value`), not derive it from a template
  - Future utility_meter chains for monthly/yearly runtime can cascade
    off these via a small intermediate `total_increasing` template if
    needed; for now the daily breakdown is the goal

Robustness:
  - If the external meter is missing or unavailable at a transition, we
    skip that interval (better to lose one cycle than corrupt the total)
  - On HA restart, in-flight intervals that started before the restart
    are lost (we have no way to know the baseline). This is acceptable
    given restarts are infrequent and one missed cycle is small.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

_COMPRESSOR_ENTITY = "binary_sensor.hph_compressor_running"
_THERMAL_NUMBER = "number.hph_thermal_runtime_today_kwh"
_ELECTRICAL_NUMBER = "number.hph_electrical_runtime_today_kwh"
_THERMAL_SOURCE_HELPER = "text.hph_src_external_thermal_energy"
_ELECTRICAL_SOURCE_HELPER = "text.hph_src_external_electrical_energy"


def _read_kwh(hass: HomeAssistant, source_helper_eid: str) -> float | None:
    """Resolve the helper to its target entity and return its float kWh.

    Returns None if any step is unavailable. Caller skips the transition.
    """
    helper = hass.states.get(source_helper_eid)
    if helper is None or not (helper.state or "").strip():
        return None
    target_eid = helper.state.strip()
    target = hass.states.get(target_eid)
    if target is None or target.state in ("unknown", "unavailable", "none", ""):
        return None
    try:
        return float(target.state)
    except (TypeError, ValueError):
        return None


async def _set_number(hass: HomeAssistant, eid: str, value: float) -> None:
    await hass.services.async_call(
        "number", "set_value",
        {"entity_id": eid, "value": round(max(value, 0), 4)},
        blocking=False,
    )


async def async_setup(hass: HomeAssistant, entry: ConfigEntry) -> list[Callable]:
    """Wire compressor-transition + midnight-reset listeners."""
    unsubs: list[Callable] = []

    # In-memory baselines for the active compressor interval. Reset to
    # None when no interval is in progress.
    state: dict[str, float | None] = {
        "thermal_baseline": None,
        "electrical_baseline": None,
    }

    @callback
    def _on_compressor_change(event: Event) -> None:
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        if old is None or new is None:
            return
        old_s = old.state
        new_s = new.state
        if old_s == "off" and new_s == "on":
            state["thermal_baseline"] = _read_kwh(hass, _THERMAL_SOURCE_HELPER)
            state["electrical_baseline"] = _read_kwh(hass, _ELECTRICAL_SOURCE_HELPER)
            _LOGGER.debug(
                "runtime_kwh: compressor on — baselines T=%s E=%s",
                state["thermal_baseline"], state["electrical_baseline"],
            )
        elif old_s == "on" and new_s == "off":
            hass.async_create_task(_close_interval())

    async def _close_interval() -> None:
        """Add (current_meter − baseline) to today's accumulator."""
        for key, src_helper, num_eid in (
            ("thermal_baseline", _THERMAL_SOURCE_HELPER, _THERMAL_NUMBER),
            ("electrical_baseline", _ELECTRICAL_SOURCE_HELPER, _ELECTRICAL_NUMBER),
        ):
            baseline = state.get(key)
            if baseline is None:
                continue  # no baseline (off→on transition was missed/skipped)
            current = _read_kwh(hass, src_helper)
            if current is None:
                state[key] = None
                continue
            delta = current - baseline
            if delta < 0:
                # Counter reset on the source — skip this interval.
                _LOGGER.warning(
                    "runtime_kwh: %s went backwards (%.3f → %.3f); skipping interval",
                    src_helper, baseline, current,
                )
                state[key] = None
                continue
            num_st = hass.states.get(num_eid)
            try:
                today = float(num_st.state) if num_st else 0.0
            except (TypeError, ValueError):
                today = 0.0
            await _set_number(hass, num_eid, today + delta)
            _LOGGER.debug("runtime_kwh: %s += %.3f kWh (today=%.3f)", num_eid, delta, today + delta)
            state[key] = None

    @callback
    def _on_midnight(now: datetime) -> None:
        hass.async_create_task(_reset_daily())

    async def _reset_daily() -> None:
        """Zero today's accumulators. If a compressor interval is still
        in progress, restart its baseline at midnight so kWh accrued
        before midnight stays on yesterday and post-midnight kWh starts
        fresh on today."""
        await _set_number(hass, _THERMAL_NUMBER, 0.0)
        await _set_number(hass, _ELECTRICAL_NUMBER, 0.0)
        comp = hass.states.get(_COMPRESSOR_ENTITY)
        if comp is not None and comp.state == "on":
            state["thermal_baseline"] = _read_kwh(hass, _THERMAL_SOURCE_HELPER)
            state["electrical_baseline"] = _read_kwh(hass, _ELECTRICAL_SOURCE_HELPER)
            _LOGGER.info(
                "runtime_kwh: midnight reset — re-baselined active interval (T=%s E=%s)",
                state["thermal_baseline"], state["electrical_baseline"],
            )
        else:
            _LOGGER.info("runtime_kwh: midnight reset")

    unsubs.append(
        async_track_state_change_event(hass, [_COMPRESSOR_ENTITY], _on_compressor_change)
    )
    unsubs.append(
        async_track_time_change(hass, _on_midnight, hour=0, minute=0, second=0)
    )

    # If the compressor is already on at coordinator start, seed baselines
    # so the current interval starts contributing as soon as it ends.
    comp = hass.states.get(_COMPRESSOR_ENTITY)
    if comp is not None and comp.state == "on":
        state["thermal_baseline"] = _read_kwh(hass, _THERMAL_SOURCE_HELPER)
        state["electrical_baseline"] = _read_kwh(hass, _ELECTRICAL_SOURCE_HELPER)
        _LOGGER.debug(
            "runtime_kwh: compressor was on at startup — baselined T=%s E=%s",
            state["thermal_baseline"], state["electrical_baseline"],
        )

    _LOGGER.debug("HPH runtime_kwh coordinator started")
    return unsubs
