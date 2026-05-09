"""HeatPump Hero — advisor coordinator.

Ports hph_advisor.yaml automations:
  - hph_dhw_on_start          (operating_mode → dhw)
  - hph_dhw_daily_rollover    (23:59 daily)
  - hph_record_heating_limit  (compressor on→off, duration ≥ 30 min, mode==heating)
"""

from __future__ import annotations

import json
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
    """Register advisor listeners. Returns unsubscribe list."""
    unsubs: list[Callable] = []

    # ── DHW on start ────────────────────────────────────────────────────────
    @callback
    def _on_mode_change(event: Event) -> None:
        new = event.data.get("new_state")
        if new is None or new.state != "dhw":
            return
        hass.async_create_task(_dhw_on_start())

    async def _dhw_on_start() -> None:
        await hass.services.async_call(
            "hph", "counter_increment",
            {"entity_id": "number.hph_dhw_fires_today"},
            blocking=True,
        )
        buf_st = hass.states.get("text.hph_dhw_start_hours")
        raw = buf_st.state if buf_st else ""
        try:
            hours: list[int] = json.loads(raw) if raw.startswith("[") else []
        except (json.JSONDecodeError, AttributeError):
            hours = []
        updated = ([dt_util.now().hour] + hours)[:14]
        await hass.services.async_call(
            "text", "set_value",
            {"entity_id": "text.hph_dhw_start_hours", "value": json.dumps(updated)},
            blocking=True,
        )

    unsubs.append(
        async_track_state_change_event(
            hass, ["sensor.hph_operating_mode"], _on_mode_change
        )
    )

    # ── DHW daily rollover at 23:59 ──────────────────────────────────────────
    @callback
    def _daily_rollover(now: datetime) -> None:
        hass.async_create_task(_do_rollover())

    async def _do_rollover() -> None:
        fires_st = hass.states.get("number.hph_dhw_fires_today")
        today_val = 0
        if fires_st and fires_st.state not in ("unknown", "unavailable"):
            try:
                today_val = int(float(fires_st.state))
            except ValueError:
                pass
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.hph_dhw_fires_yesterday", "value": today_val},
            blocking=True,
        )
        await hass.services.async_call(
            "hph", "counter_reset",
            {"entity_id": "number.hph_dhw_fires_today"},
            blocking=True,
        )

    unsubs.append(async_track_time_change(hass, _daily_rollover, hour=23, minute=59, second=0))

    # ── Record heating-limit observation (compressor on→off) ────────────────
    @callback
    def _on_compressor_off(event: Event) -> None:
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        if old is None or new is None:
            return
        if not (old.state == "on" and new.state == "off"):
            return
        hass.async_create_task(_record_heating_limit())

    async def _record_heating_limit() -> None:
        duration_st = hass.states.get("number.hph_cycle_last_duration_min")
        if not duration_st or duration_st.state in ("unknown", "unavailable"):
            return
        try:
            duration = float(duration_st.state)
        except ValueError:
            return
        if duration < 30:
            return
        outdoor_st = hass.states.get("sensor.hph_source_outdoor_temp")
        if not outdoor_st or outdoor_st.state in ("unknown", "unavailable", "none"):
            return
        mode_st = hass.states.get("sensor.hph_operating_mode")
        if not mode_st or mode_st.state != "heating":
            return
        try:
            outdoor_temp = float(outdoor_st.state)
        except ValueError:
            return
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.hph_heating_limit_observed_c", "value": outdoor_temp},
            blocking=True,
        )

    unsubs.append(
        async_track_state_change_event(
            hass, ["binary_sensor.hph_compressor_running"], _on_compressor_off
        )
    )

    _LOGGER.debug("HPH advisor coordinator started")
    return unsubs
