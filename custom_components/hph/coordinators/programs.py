"""HeatPump Hero — programs coordinator.

Manages two programs:
  - Screed dry-out: multi-day supply-temperature ramp per ISO EN 1264-4 / DIN 18560-1.
  - Legionella protection schedule: weekly DHW boost at a user-configured weekday/hour.
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

_WEEKDAY_INDEX = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
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

    # ── Legionella: hourly tick, fires the boost on the configured weekday/hour ─
    @callback
    def _legionella_tick(now: datetime) -> None:
        if _st(hass, "switch.hph_prog_legionella") != "on":
            return
        configured_hour = int(_flt(hass, "number.hph_prog_legionella_hour", 3))
        if now.hour != configured_hour:
            return
        weekday_key = _st(hass, "select.hph_prog_legionella_weekday")
        configured_wd = _WEEKDAY_INDEX.get(weekday_key, 6)
        if now.weekday() != configured_wd:
            return
        hass.async_create_task(_run_legionella_schedule())

    async def _run_legionella_schedule() -> None:
        target_c = _flt(hass, "number.hph_prog_legionella_target_c", 65.0)

        dhw_holder = hass.states.get("text.hph_ctrl_write_dhw_target")
        if dhw_holder and dhw_holder.state not in ("unknown", "unavailable", ""):
            dhw_eid = dhw_holder.state.strip()
            if dhw_eid:
                try:
                    await hass.services.async_call(
                        "number", "set_value",
                        {"entity_id": dhw_eid, "value": target_c},
                        blocking=False,
                    )
                    _LOGGER.info("legionella schedule: set %s → %.0f °C", dhw_eid, target_c)
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning("legionella schedule: set DHW target failed: %s", exc)

        force_holder = hass.states.get("text.hph_ctrl_write_force_dhw")
        if force_holder and force_holder.state not in ("unknown", "unavailable", ""):
            force_eid = force_holder.state.strip()
            if force_eid:
                try:
                    await hass.services.async_call(
                        "button", "press", {"entity_id": force_eid}, blocking=False,
                    )
                    _LOGGER.info("legionella schedule: triggered %s", force_eid)
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning("legionella schedule: force-DHW press failed: %s", exc)

        try:
            await hass.services.async_call(
                "datetime", "set_value",
                {
                    "entity_id": "datetime.hph_prog_legionella_last_run",
                    "datetime": dt_util.now().isoformat(),
                },
                blocking=True,
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("legionella schedule: timestamp update failed: %s", exc)

        hold_min = int(_flt(hass, "number.hph_prog_legionella_hold_min", 30))
        weekday_key = _st(hass, "select.hph_prog_legionella_weekday")
        await hass.services.async_call(
            "persistent_notification", "create",
            {
                "notification_id": "hph_prog_legionella",
                "title": "HPH legionella program triggered",
                "message": (
                    f"Weekly anti-legionella DHW boost started on {weekday_key}. "
                    f"Target: {target_c:.0f} °C, hold: {hold_min} min. "
                    "Check your DHW temperature to confirm the heat pump responded."
                ),
            },
            blocking=True,
        )

    # Fires at minute=0, second=0 every hour — weekday/hour check inside the callback.
    unsubs.append(async_track_time_change(hass, _legionella_tick, minute=0, second=0))

    _LOGGER.debug("HPH programs coordinator started")
    return unsubs
