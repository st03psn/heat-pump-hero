"""HeatPump Hero — programs coordinator.

Screed dry-out program only.
Legionella protection is handled by the heat pump's own built-in schedule.
The manual one-off trigger (run_legionella_now service) lives in __init__.py.
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

_PROFILE_DAYS = {
    "functional_3d": 3,
    "combined_10d": 10,
    "din_18560_28d": 28,
}


def _st(hass: HomeAssistant, eid: str) -> str:
    s = hass.states.get(eid)
    return s.state if s else "unknown"


def _flt(hass: HomeAssistant, eid: str, default: float = 0.0) -> float:
    try:
        return float(_st(hass, eid))
    except (ValueError, TypeError):
        return default


def _resolve(hass: HomeAssistant, holder: str) -> str:
    return _st(hass, holder)


async def async_setup(hass: HomeAssistant, entry: ConfigEntry) -> list[Callable]:
    """Register screed program listeners. Returns unsubscribe list."""
    unsubs: list[Callable] = []

    # ── Screed arm: switch off→on ────────────────────────────────────────────
    @callback
    def _on_screed_switch(event: Event) -> None:
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        if old is None or new is None:
            return
        if not (old.state == "off" and new.state == "on"):
            return
        if _st(hass, "switch.hph_ctrl_master") != "on":
            return
        hass.async_create_task(_arm_screed())

    async def _arm_screed() -> None:
        await hass.services.async_call(
            "datetime", "set_value",
            {"entity_id": "datetime.hph_prog_screed_start", "datetime": dt_util.now().isoformat()},
            blocking=True,
        )
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.hph_prog_screed_day", "value": 1},
            blocking=True,
        )
        await hass.services.async_call(
            "switch", "turn_on",
            {"entity_id": "switch.hph_prog_screed_active"},
            blocking=True,
        )
        profile = _st(hass, "select.hph_prog_screed_profile")
        await hass.services.async_call(
            "persistent_notification", "create",
            {
                "notification_id": "hph_prog_screed",
                "title": "HPH screed program armed",
                "message": (
                    f"Profile {profile} armed on day 1. "
                    "Day will advance daily at 00:01. "
                    "Disable switch.hph_prog_screed to abort early."
                ),
            },
            blocking=True,
        )

    unsubs.append(
        async_track_state_change_event(
            hass, ["switch.hph_prog_screed"], _on_screed_switch
        )
    )

    # ── Screed daily advance: 00:01 ──────────────────────────────────────────
    @callback
    def _screed_daily(now: datetime) -> None:
        if (
            _st(hass, "switch.hph_prog_screed") != "on"
            or _st(hass, "switch.hph_prog_screed_active") != "on"
        ):
            return
        hass.async_create_task(_advance_screed())

    async def _advance_screed() -> None:
        d = int(_flt(hass, "number.hph_prog_screed_day", 0)) + 1
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.hph_prog_screed_day", "value": d},
            blocking=True,
        )
        screed_tgt_st = hass.states.get("sensor.hph_prog_screed_target")
        tgt = 0.0
        if screed_tgt_st and screed_tgt_st.state not in ("unknown", "unavailable"):
            try:
                tgt = float(screed_tgt_st.state)
            except ValueError:
                pass
        high_entity = _resolve(hass, "text.hph_ctrl_write_z1_curve_high")
        if tgt > 0 and high_entity not in ("", "unknown", "unavailable", "none"):
            await hass.services.async_call(
                "number", "set_value",
                {"entity_id": high_entity, "value": tgt},
                blocking=True,
            )
        profile = _st(hass, "select.hph_prog_screed_profile")
        last_day = _PROFILE_DAYS.get(profile, 0)
        if d >= last_day:
            await hass.services.async_call(
                "switch", "turn_off",
                {"entity_id": "switch.hph_prog_screed_active"},
                blocking=True,
            )
            await hass.services.async_call(
                "number", "set_value",
                {"entity_id": "number.hph_prog_screed_day", "value": 0},
                blocking=True,
            )
            await hass.services.async_call(
                "persistent_notification", "create",
                {
                    "notification_id": "hph_prog_screed",
                    "title": "HPH screed program — completed",
                    "message": (
                        f"Profile {profile} finished after {last_day} days. "
                        "Heating curve was returned to user defaults — verify the "
                        "target_high value under Configuration."
                    ),
                },
                blocking=True,
            )

    unsubs.append(async_track_time_change(hass, _screed_daily, hour=0, minute=1, second=0))

    _LOGGER.debug("HPH programs coordinator started (screed only)")
    return unsubs
