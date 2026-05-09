"""HeatPump Hero — control extensions coordinator.

Ports hph_control_extensions.yaml automations:
  - hph_ctrl_adaptive_curve_apply      (Sunday 04:00)
  - hph_ctrl_price_dhw_check           (every hour at :05)
  - hph_ctrl_price_dhw_reset_daily     (00:01 daily)
  - hph_ctrl_forecast_preheat_enable   (every 15 min; 4h revert delay)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

_forecast_task: asyncio.Task | None = None


def _st(hass: HomeAssistant, eid: str) -> str:
    s = hass.states.get(eid)
    return s.state if s else "unknown"


def _flt(hass: HomeAssistant, eid: str, default: float = 0.0) -> float:
    try:
        return float(_st(hass, eid))
    except (ValueError, TypeError):
        return default


def _resolve(hass: HomeAssistant, holder: str) -> str:
    """Return the entity_id stored inside a text helper."""
    return _st(hass, holder)


async def async_setup(hass: HomeAssistant, entry: ConfigEntry) -> list[Callable]:
    """Register control-extension listeners. Returns unsubscribe list."""
    global _forecast_task
    unsubs: list[Callable] = []

    # ── Adaptive curve: Sunday 04:00 ────────────────────────────────────────
    @callback
    def _adaptive_curve_trigger(now: datetime) -> None:
        if now.weekday() != 6:  # 6 = Sunday
            return
        if (
            _st(hass, "switch.hph_ctrl_master") != "on"
            or _st(hass, "switch.hph_ctrl_adaptive_curve") != "on"
        ):
            return
        # Check recommendation magnitude
        adv_st = hass.states.get("sensor.hph_advisor_analysis")
        rec_k = 0.0
        if adv_st:
            try:
                rec_k = float(adv_st.attributes.get("recommendation_k", 0))
            except (TypeError, ValueError):
                pass
        if abs(rec_k) < 0.3:
            return
        # Cooldown: not within last 6 days
        last_st = hass.states.get("datetime.hph_ctrl_adaptive_last_run")
        if last_st and last_st.state not in ("unknown", "unavailable", ""):
            try:
                last = dt_util.parse_datetime(last_st.state)
                if last and (dt_util.now() - last).total_seconds() <= 86400 * 6:
                    return
            except Exception:  # noqa: BLE001
                pass
        hass.async_create_task(_apply_adaptive_curve(rec_k))

    async def _apply_adaptive_curve(rec_k: float) -> None:
        max_step = _flt(hass, "number.hph_ctrl_adaptive_max_step_k", 0.5)
        step = min(rec_k, max_step) if rec_k > 0 else max(rec_k, -max_step)
        supply_min = _flt(hass, "number.hph_ctrl_adaptive_supply_min_c", 22)
        supply_max = _flt(hass, "number.hph_ctrl_adaptive_supply_max_c", 50)
        high_min = supply_min + 5
        low_max = supply_max - 5

        high_entity = _resolve(hass, "text.hph_ctrl_write_z1_curve_high")
        low_entity = _resolve(hass, "text.hph_ctrl_write_z1_curve_low")
        cur_high = _flt(hass, high_entity, 35)
        cur_low = _flt(hass, low_entity, 25)
        new_high = round(max(min(cur_high + step, supply_max), high_min), 1)
        new_low = round(max(min(cur_low + step, low_max), supply_min), 1)

        if high_entity not in ("unknown", "unavailable", ""):
            await hass.services.async_call(
                "number", "set_value",
                {"entity_id": high_entity, "value": new_high},
                blocking=True,
            )
        if low_entity not in ("unknown", "unavailable", ""):
            await hass.services.async_call(
                "number", "set_value",
                {"entity_id": low_entity, "value": new_low},
                blocking=True,
            )
        await hass.services.async_call(
            "datetime", "set_value",
            {"entity_id": "datetime.hph_ctrl_adaptive_last_run", "datetime": dt_util.now().isoformat()},
            blocking=True,
        )
        await hass.services.async_call(
            "persistent_notification", "create",
            {
                "notification_id": "hph_adaptive_curve",
                "title": "HPH adaptive curve applied",
                "message": (
                    f"Heating curve shifted by **{step} K** (recommendation was {rec_k} K). "
                    f"Target high {cur_high} → {new_high} °C, target low {cur_low} → {new_low} °C. "
                    "Next adjustment possible after 6 days. "
                    "Disable switch.hph_ctrl_adaptive_curve to halt self-learning."
                ),
            },
            blocking=True,
        )

    unsubs.append(async_track_time_change(hass, _adaptive_curve_trigger, hour=4, minute=0, second=0))

    # ── Price DHW: every hour at :05 ────────────────────────────────────────
    @callback
    def _price_dhw_tick(now: datetime) -> None:
        if now.minute != 5:
            return
        if (
            _st(hass, "switch.hph_ctrl_master") != "on"
            or _st(hass, "switch.hph_ctrl_price_dhw") != "on"
        ):
            return
        price_holder = _st(hass, "text.hph_ctrl_price_entity")
        mean_holder = _st(hass, "text.hph_ctrl_price_mean_entity")
        if price_holder in ("unknown", "unavailable", "") or mean_holder in ("unknown", "unavailable", ""):
            return
        price = _flt(hass, price_holder)
        mean = _flt(hass, mean_holder)
        factor = _flt(hass, "number.hph_ctrl_price_threshold_factor", 0.85)
        if mean <= 0 or price >= mean * factor:
            return
        dhw_target_holder = _st(hass, "text.hph_src_dhw_target_temp")
        dhw_temp = _flt(hass, "sensor.hph_source_dhw_temp", 99)
        dhw_tgt = _flt(hass, dhw_target_holder, 50) if dhw_target_holder not in ("unknown", "unavailable", "") else 50
        if dhw_temp >= dhw_tgt - 5:
            return
        max_fires = int(_flt(hass, "number.hph_ctrl_price_max_per_day", 1))
        fired_today = int(_flt(hass, "number.hph_ctrl_price_dhw_fires_today"))
        if fired_today >= max_fires:
            return
        hass.async_create_task(_fire_price_dhw(price, factor))

    async def _fire_price_dhw(price: float, factor: float) -> None:
        force_entity = _resolve(hass, "text.hph_ctrl_write_force_dhw")
        if force_entity not in ("unknown", "unavailable", ""):
            await hass.services.async_call(
                "button", "press", {"entity_id": force_entity}, blocking=True
            )
        await hass.services.async_call(
            "hph", "counter_increment",
            {"entity_id": "number.hph_ctrl_price_dhw_fires_today"},
            blocking=True,
        )
        await hass.services.async_call(
            "datetime", "set_value",
            {"entity_id": "datetime.hph_ctrl_price_dhw_last_fire", "datetime": dt_util.now().isoformat()},
            blocking=True,
        )
        await hass.services.async_call(
            "persistent_notification", "create",
            {
                "notification_id": "hph_price_dhw",
                "title": "HPH price-DHW fired",
                "message": f"DHW boost forced — current price {price} is below daily mean × {factor}.",
            },
            blocking=True,
        )

    unsubs.append(
        async_track_time_interval(hass, _price_dhw_tick, timedelta(minutes=1))
    )

    # ── Price DHW daily reset: 00:01 ────────────────────────────────────────
    @callback
    def _price_dhw_reset(now: datetime) -> None:
        hass.async_create_task(
            hass.services.async_call(
                "hph", "counter_reset",
                {"entity_id": "number.hph_ctrl_price_dhw_fires_today"},
                blocking=True,
            )
        )

    unsubs.append(async_track_time_change(hass, _price_dhw_reset, hour=0, minute=1, second=0))

    # ── Forecast preheat: every 15 min ──────────────────────────────────────
    @callback
    def _forecast_tick(now: datetime) -> None:
        global _forecast_task
        if now.minute % 15 != 0:
            return
        if (
            _st(hass, "switch.hph_ctrl_master") != "on"
            or _st(hass, "switch.hph_ctrl_forecast_preheat") != "on"
        ):
            return
        fc_holder = _st(hass, "text.hph_ctrl_forecast_entity")
        if fc_holder in ("unknown", "unavailable", ""):
            return
        cur_temp = _flt(hass, "sensor.hph_source_outdoor_temp", 99)
        fc_temp = _flt(hass, fc_holder, 99)
        threshold = _flt(hass, "number.hph_ctrl_forecast_drop_threshold_k", 8)
        if (cur_temp - fc_temp) < threshold or cur_temp <= 0:
            return
        if _st(hass, "switch.hph_ctrl_forecast_preheat_active") == "on":
            return
        if _forecast_task is not None and not _forecast_task.done():
            return
        _forecast_task = hass.async_create_task(_forecast_preheat_run(cur_temp))

    async def _forecast_preheat_run(original_temp: float) -> None:
        boost = _flt(hass, "number.hph_ctrl_forecast_boost_k", 2)
        high_entity = _resolve(hass, "text.hph_ctrl_write_z1_curve_high")
        cur_high = _flt(hass, high_entity, 35) if high_entity not in ("unknown", "unavailable", "") else 35
        boosted = round(cur_high + boost, 1)

        await hass.services.async_call(
            "switch", "turn_on",
            {"entity_id": "switch.hph_ctrl_forecast_preheat_active"},
            blocking=True,
        )
        if high_entity not in ("unknown", "unavailable", ""):
            await hass.services.async_call(
                "number", "set_value",
                {"entity_id": high_entity, "value": boosted},
                blocking=True,
            )
        await hass.services.async_call(
            "persistent_notification", "create",
            {
                "notification_id": "hph_forecast_preheat",
                "title": "HPH forecast pre-heat engaged",
                "message": f"Curve boosted by {boost} K for 4 hours — cold front incoming.",
            },
            blocking=True,
        )
        await asyncio.sleep(4 * 3600)
        if high_entity not in ("unknown", "unavailable", ""):
            await hass.services.async_call(
                "number", "set_value",
                {"entity_id": high_entity, "value": cur_high},
                blocking=True,
            )
        await hass.services.async_call(
            "switch", "turn_off",
            {"entity_id": "switch.hph_ctrl_forecast_preheat_active"},
            blocking=True,
        )

    unsubs.append(
        async_track_time_interval(hass, _forecast_tick, timedelta(minutes=1))
    )

    _LOGGER.debug("HPH control_ext coordinator started")
    return unsubs
