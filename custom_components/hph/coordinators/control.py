"""HeatPump Hero — control coordinator.

Ports hph_control.yaml automations:
  - hph_ctrl_ccc_block_short_pause  (compressor off→on, CCC enabled)
  - hph_ctrl_softstart              (compressor off→on, softstart enabled)
  - hph_ctrl_solar_dhw              (template: PV > threshold for 5 min)
  - hph_ctrl_quiet_night_on         (22:00 daily)
  - hph_ctrl_quiet_night_off        (06:00 daily)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util
from datetime import timedelta

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

_ccc_task: asyncio.Task | None = None
_softstart_task: asyncio.Task | None = None
_solar_dhw_task: asyncio.Task | None = None
_solar_above_since: datetime | None = None


def _state(hass: HomeAssistant, entity_id: str) -> str:
    st = hass.states.get(entity_id)
    return st.state if st else "unknown"


def _float_state(hass: HomeAssistant, entity_id: str, default: float = 0.0) -> float:
    v = _state(hass, entity_id)
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _write_entity(hass: HomeAssistant, entity_id: str) -> str:
    """Resolve entity_id stored in a text helper."""
    return _state(hass, entity_id)


async def async_setup(hass: HomeAssistant, entry: ConfigEntry) -> list[Callable]:
    """Register control listeners. Returns unsubscribe list."""
    global _ccc_task, _softstart_task, _solar_dhw_task, _solar_above_since
    unsubs: list[Callable] = []

    # ── CCC + SoftStart: compressor off→on ──────────────────────────────────
    @callback
    def _on_compressor_on(event: Event) -> None:
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        if old is None or new is None:
            return
        if not (old.state == "off" and new.state == "on"):
            return
        # CCC
        if (
            _state(hass, "switch.hph_ctrl_master") == "on"
            and _state(hass, "switch.hph_ctrl_ccc") == "on"
        ):
            pause = _float_state(hass, "number.hph_cycle_last_pause_min", 99)
            min_pause = _float_state(hass, "number.hph_ctrl_ccc_min_pause_min", 15)
            if pause < min_pause:
                global _ccc_task
                if _ccc_task is None or _ccc_task.done():
                    _ccc_task = hass.async_create_task(_ccc_quiet_block())
        # SoftStart
        if (
            _state(hass, "switch.hph_ctrl_master") == "on"
            and _state(hass, "switch.hph_ctrl_softstart") == "on"
        ):
            global _softstart_task
            if _softstart_task is None or _softstart_task.done():
                _softstart_task = hass.async_create_task(_softstart_ramp())

    async def _ccc_quiet_block() -> None:
        quiet_entity = _write_entity(hass, "text.hph_ctrl_write_quiet_mode")
        if quiet_entity in ("unknown", "unavailable", ""):
            return
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": quiet_entity, "option": "3"},
            blocking=True,
        )
        await hass.services.async_call(
            "persistent_notification", "create",
            {
                "title": "HeatPump Hero CCC",
                "message": "Short pause detected — Quiet-Mode engaged for 5 minutes.",
            },
            blocking=True,
        )
        await asyncio.sleep(300)
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": quiet_entity, "option": "0"},
            blocking=True,
        )

    async def _softstart_ramp() -> None:
        quiet_entity = _write_entity(hass, "text.hph_ctrl_write_quiet_mode")
        if quiet_entity in ("unknown", "unavailable", ""):
            return
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": quiet_entity, "option": "2"},
            blocking=True,
        )
        await asyncio.sleep(600)
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": quiet_entity, "option": "0"},
            blocking=True,
        )

    unsubs.append(
        async_track_state_change_event(
            hass, ["binary_sensor.hph_compressor_running"], _on_compressor_on
        )
    )

    # ── Solar DHW: PV surplus > threshold for 5 minutes ────────────────────
    @callback
    def _check_solar_dhw(now: datetime) -> None:
        """Called every minute to implement 'for: 00:05:00' template trigger."""
        global _solar_above_since, _solar_dhw_task

        if (
            _state(hass, "switch.hph_ctrl_master") != "on"
            or _state(hass, "switch.hph_ctrl_solar_dhw") != "on"
        ):
            _solar_above_since = None
            return

        pv_entity = _state(hass, "text.hph_ctrl_pv_surplus_entity")
        threshold = _float_state(hass, "number.hph_ctrl_solar_pv_threshold_w", 1500)
        pv_power = _float_state(hass, pv_entity) if pv_entity else 0.0
        dhw_temp = _float_state(hass, "sensor.hph_source_dhw_temp", 99)

        above = pv_entity and pv_power > threshold
        if not above:
            _solar_above_since = None
            return

        if _solar_above_since is None:
            _solar_above_since = dt_util.now()
            return

        elapsed = (dt_util.now() - _solar_above_since).total_seconds()
        if elapsed < 300:
            return

        if dhw_temp >= 55:
            return

        if _solar_dhw_task is not None and not _solar_dhw_task.done():
            return

        _solar_above_since = None  # reset so it doesn't re-fire immediately
        _solar_dhw_task = hass.async_create_task(_fire_solar_dhw())

    async def _fire_solar_dhw() -> None:
        force_entity = _write_entity(hass, "text.hph_ctrl_write_force_dhw")
        if force_entity not in ("unknown", "unavailable", ""):
            await hass.services.async_call(
                "button", "press", {"entity_id": force_entity}, blocking=True
            )
        await hass.services.async_call(
            "persistent_notification", "create",
            {
                "title": "HeatPump Hero Solar-DHW",
                "message": "PV surplus detected — DHW force triggered.",
            },
            blocking=True,
        )

    unsubs.append(
        async_track_time_interval(hass, _check_solar_dhw, timedelta(minutes=1))
    )

    # ── Quiet night on/off ───────────────────────────────────────────────────
    @callback
    def _quiet_night_on(now: datetime) -> None:
        if (
            _state(hass, "switch.hph_ctrl_master") != "on"
            or _state(hass, "switch.hph_ctrl_quiet_night") != "on"
        ):
            return
        hass.async_create_task(_set_quiet("3"))

    @callback
    def _quiet_night_off(now: datetime) -> None:
        if (
            _state(hass, "switch.hph_ctrl_master") != "on"
            or _state(hass, "switch.hph_ctrl_quiet_night") != "on"
        ):
            return
        hass.async_create_task(_set_quiet("0"))

    async def _set_quiet(option: str) -> None:
        quiet_entity = _write_entity(hass, "text.hph_ctrl_write_quiet_mode")
        if quiet_entity not in ("unknown", "unavailable", ""):
            await hass.services.async_call(
                "select", "select_option",
                {"entity_id": quiet_entity, "option": option},
                blocking=True,
            )

    unsubs.append(async_track_time_change(hass, _quiet_night_on, hour=22, minute=0, second=0))
    unsubs.append(async_track_time_change(hass, _quiet_night_off, hour=6, minute=0, second=0))

    _LOGGER.debug("HPH control coordinator started")
    return unsubs
