"""HeatPump Hero — programs coordinator.

Ports hph_programs.yaml automations:
  - hph_prog_legionella_run   (hourly at :00, with wait_template up to 4h)
  - hph_prog_screed_arm       (switch.hph_prog_screed off→on)
  - hph_prog_screed_daily     (00:01 daily)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

_legionella_task: asyncio.Task | None = None


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
    """Register program listeners. Returns unsubscribe list."""
    global _legionella_task
    unsubs: list[Callable] = []

    # ── Legionella: hourly at :00 ────────────────────────────────────────────
    _WEEKDAY_MAP = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    @callback
    def _legionella_tick(now: datetime) -> None:
        global _legionella_task
        if now.minute != 0:
            return
        if (
            _st(hass, "switch.hph_ctrl_master") != "on"
            or _st(hass, "switch.hph_prog_legionella") != "on"
        ):
            return
        wd_setting = _st(hass, "select.hph_prog_legionella_weekday")
        wd_now = _WEEKDAY_MAP[now.weekday()]
        if wd_setting != wd_now:
            return
        target_hour = int(_flt(hass, "number.hph_prog_legionella_hour", 3))
        if now.hour != target_hour:
            return
        last_st = hass.states.get("datetime.hph_prog_legionella_last_run")
        if last_st and last_st.state not in ("unknown", "unavailable", ""):
            try:
                last = dt_util.parse_datetime(last_st.state)
                if last and (dt_util.now() - last).total_seconds() <= 86400 * 6:
                    return
            except Exception:  # noqa: BLE001
                pass
        if _legionella_task is None or _legionella_task.done():
            _legionella_task = hass.async_create_task(_run_legionella())

    async def _run_legionella() -> None:
        target = _flt(hass, "number.hph_prog_legionella_target_c", 65)
        hold = int(_flt(hass, "number.hph_prog_legionella_hold_min", 30))
        dhw_target_entity = _resolve(hass, "text.hph_ctrl_write_dhw_target")
        force_dhw_entity = _resolve(hass, "text.hph_ctrl_write_force_dhw")

        if dhw_target_entity not in ("", "unknown", "unavailable", "none"):
            await hass.services.async_call(
                "number", "set_value",
                {"entity_id": dhw_target_entity, "value": target},
                blocking=True,
            )
        if force_dhw_entity not in ("", "unknown", "unavailable", "none"):
            await hass.services.async_call(
                "button", "press", {"entity_id": force_dhw_entity}, blocking=True
            )

        # wait_template: poll DHW temp up to 4h
        deadline = dt_util.now() + timedelta(hours=4)
        reached = False
        while dt_util.now() < deadline:
            dhw_temp = _flt(hass, "sensor.hph_source_dhw_temp", 0)
            if dhw_temp >= target:
                reached = True
                break
            await asyncio.sleep(60)

        if reached:
            await asyncio.sleep(hold * 60)
            await hass.services.async_call(
                "datetime", "set_value",
                {"entity_id": "datetime.hph_prog_legionella_last_run", "datetime": dt_util.now().isoformat()},
                blocking=True,
            )
            await hass.services.async_call(
                "persistent_notification", "create",
                {
                    "notification_id": "hph_prog_legionella",
                    "title": "HPH legionella program — completed",
                    "message": f"Tank reached {target} °C and was held for {hold} min. Logged as last successful run.",
                },
                blocking=True,
            )
        else:
            await hass.services.async_call(
                "persistent_notification", "create",
                {
                    "notification_id": "hph_prog_legionella",
                    "title": "HPH legionella program — incomplete",
                    "message": (
                        f"Tank did not reach {target} °C within 4 h. "
                        "Check the heat-pump's DHW target ceiling and that the source helper "
                        "text.hph_ctrl_write_dhw_target points to a valid number entity. "
                        "Last run NOT updated."
                    ),
                },
                blocking=True,
            )

    unsubs.append(
        async_track_time_interval(hass, _legionella_tick, timedelta(minutes=1))
    )

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
    _PROFILE_DAYS = {
        "functional_3d": 3,
        "combined_10d": 10,
        "din_18560_28d": 28,
    }

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
        # Apply target supply temp for today
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

    _LOGGER.debug("HPH programs coordinator started")
    return unsubs
