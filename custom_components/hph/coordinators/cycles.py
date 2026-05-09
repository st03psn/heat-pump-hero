"""HeatPump Hero — compressor cycle tracking coordinator.

Ports hph_cycles.yaml automations:
  - hph_cycle_on_start   (compressor off→on)
  - hph_cycle_on_stop    (compressor on→off)
  - hph_cycles_daily_reset (00:00 daily)
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
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, entry: ConfigEntry) -> list[Callable]:
    """Register cycle-tracking listeners. Returns unsubscribe list."""
    unsubs: list[Callable] = []

    @callback
    def _on_compressor_change(event: Event) -> None:
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        if old is None or new is None:
            return
        if old.state == "off" and new.state == "on":
            hass.async_create_task(_cycle_start())
        elif old.state == "on" and new.state == "off":
            hass.async_create_task(_cycle_stop())

    async def _cycle_start() -> None:
        now_str = dt_util.now().isoformat()
        await hass.services.async_call(
            "datetime", "set_value",
            {"entity_id": "datetime.hph_cycle_last_start", "datetime": now_str},
            blocking=True,
        )
        # Compute pause from last cycle end
        last_end_st = hass.states.get("datetime.hph_cycle_last_end")
        pause_min = 0.0
        if last_end_st and last_end_st.state not in ("unknown", "unavailable", "none", ""):
            try:
                last_end = dt_util.parse_datetime(last_end_st.state)
                if last_end:
                    pause_min = round(
                        (dt_util.now() - last_end).total_seconds() / 60, 1
                    )
            except Exception:  # noqa: BLE001
                pass
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.hph_cycle_last_pause_min", "value": pause_min},
            blocking=True,
        )
        await hass.services.async_call(
            "hph", "counter_increment",
            {"entity_id": "number.hph_cycles_today"},
            blocking=True,
        )

    async def _cycle_stop() -> None:
        now_str = dt_util.now().isoformat()
        await hass.services.async_call(
            "datetime", "set_value",
            {"entity_id": "datetime.hph_cycle_last_end", "datetime": now_str},
            blocking=True,
        )
        last_start_st = hass.states.get("datetime.hph_cycle_last_start")
        duration_min = 0.0
        if last_start_st and last_start_st.state not in ("unknown", "unavailable", "none", ""):
            try:
                last_start = dt_util.parse_datetime(last_start_st.state)
                if last_start:
                    duration_min = round(
                        (dt_util.now() - last_start).total_seconds() / 60, 1
                    )
            except Exception:  # noqa: BLE001
                pass
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.hph_cycle_last_duration_min", "value": duration_min},
            blocking=True,
        )
        threshold_st = hass.states.get("number.hph_cycle_short_threshold_min")
        threshold = 10.0
        if threshold_st and threshold_st.state not in ("unknown", "unavailable"):
            try:
                threshold = float(threshold_st.state)
            except ValueError:
                pass
        if 0 < duration_min < threshold:
            await hass.services.async_call(
                "hph", "counter_increment",
                {"entity_id": "number.hph_short_cycles_today"},
                blocking=True,
            )

    unsubs.append(
        async_track_state_change_event(
            hass, ["binary_sensor.hph_compressor_running"], _on_compressor_change
        )
    )

    @callback
    def _daily_reset(now: datetime) -> None:
        hass.async_create_task(_do_daily_reset())

    async def _do_daily_reset() -> None:
        await hass.services.async_call(
            "hph", "counter_reset",
            {"entity_id": ["number.hph_cycles_today", "number.hph_short_cycles_today"]},
            blocking=True,
        )

    unsubs.append(async_track_time_change(hass, _daily_reset, hour=0, minute=0, second=0))

    _LOGGER.debug("HPH cycles coordinator started")
    return unsubs
