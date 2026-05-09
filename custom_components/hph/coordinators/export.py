"""HeatPump Hero — export coordinator.

Ports hph_export.yaml automations:
  - hph_export_daily    (03:00, if schedule == daily_0300)
  - hph_export_weekly   (03:00 Monday, if schedule == weekly_monday_0300)
  - hph_export_monthly  (03:00 on 1st, if schedule == monthly_1st_0300)

The export itself delegates to the hph.export_now service, which is
implemented in helpers/export.py and registered in __init__.py.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


def _st(hass: HomeAssistant, eid: str) -> str:
    s = hass.states.get(eid)
    return s.state if s else "unknown"


async def async_setup(hass: HomeAssistant, entry: ConfigEntry) -> list[Callable]:
    """Register export schedule listeners. Returns unsubscribe list."""
    unsubs: list[Callable] = []

    @callback
    def _export_trigger(now: datetime) -> None:
        schedule = _st(hass, "select.hph_export_schedule")
        should_fire = False
        if schedule == "daily_0300":
            should_fire = True
        elif schedule == "weekly_monday_0300" and now.weekday() == 0:
            should_fire = True
        elif schedule == "monthly_1st_0300" and now.day == 1:
            should_fire = True
        if should_fire:
            hass.async_create_task(
                hass.services.async_call("hph", "export_now", {}, blocking=True)
            )

    unsubs.append(async_track_time_change(hass, _export_trigger, hour=3, minute=0, second=0))

    _LOGGER.debug("HPH export coordinator started")
    return unsubs
