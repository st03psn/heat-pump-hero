"""HeatPump Hero — bridge coordinator.

Ports hph_bridge.yaml scripts + automations:
  - hph_bridge_publish_state    (state changes on whitelist entities)
  - hph_bridge_publish_initial  (HA start + bridge switch on)
  - hph_bridge_clear_on_disable (bridge switch off)

Requires mqtt integration to be loaded; silently skips if MQTT unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable

from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

_BRIDGE_ENTITIES = [
    "sensor.hph_thermal_power",
    "sensor.hph_operating_mode",
    "binary_sensor.hph_compressor_running",
    "binary_sensor.hph_defrost_active",
    "sensor.hph_cop_live",
    "sensor.hph_cop_daily",
    "sensor.hph_cop_monthly",
    "sensor.hph_scop",
    "sensor.hph_cop_monthly_heating",
    "sensor.hph_cop_yearly_heating",
    "sensor.hph_cop_monthly_dhw",
    "sensor.hph_cop_yearly_dhw",
    "sensor.hph_cop_last_month",
    "sensor.hph_cop_last_year",
    "sensor.hph_thermal_daily",
    "sensor.hph_thermal_monthly",
    "sensor.hph_thermal_yearly",
    "sensor.hph_thermal_last_month",
    "sensor.hph_thermal_last_year",
    "sensor.hph_electrical_daily",
    "sensor.hph_electrical_monthly",
    "sensor.hph_electrical_yearly",
    "sensor.hph_electrical_last_month",
    "sensor.hph_electrical_last_year",
    "sensor.hph_cop_change_month_pct",
    "sensor.hph_scop_change_year_pct",
    "sensor.hph_avg_cycle_duration_24h",
    "sensor.hph_short_cycle_ratio",
    "sensor.hph_cycles_today",
    "sensor.hph_short_cycles_today",
    "sensor.hph_advisor_summary",
    "sensor.hph_advisor_short_cycle",
    "sensor.hph_advisor_spread",
    "sensor.hph_advisor_defrost",
    "sensor.hph_advisor_heat_curve",
    "sensor.hph_advisor_dhw_runtime",
    "sensor.hph_advisor_heating_limit",
    "sensor.hph_advisor_diagnostics",
    "sensor.hph_advisor_pressure_trend",
    "sensor.hph_advisor_analysis",
    "sensor.hph_pressure_delta_7d",
    "sensor.hph_diagnostics_current_error",
    "sensor.hph_diagnostics_recurrence",
    "sensor.hph_indoor_temp_deviation",
    "sensor.hph_indoor_deviation_smoothed",
    "sensor.hph_schema_variant_active",
    "sensor.hph_model_refrigerant",
    "sensor.hph_model_description",
]


async def async_setup(hass: HomeAssistant, entry: ConfigEntry) -> list[Callable]:
    """Register bridge listeners. Returns unsubscribe list."""
    unsubs: list[Callable] = []

    def _bridge_enabled() -> bool:
        s = hass.states.get("switch.hph_bridge_enabled")
        return s is not None and s.state == "on"

    def _prefix() -> str:
        s = hass.states.get("text.hph_bridge_prefix")
        return s.state if s and s.state not in ("unknown", "unavailable", "") else "hph"

    async def _publish_one(entity_id: str, clear: bool = False) -> None:
        prefix = _prefix()
        topic_base = f"{prefix}/{entity_id.replace('.', '/')}"
        payload = ""
        attr_payload = "{}"
        if not clear:
            st = hass.states.get(entity_id)
            if st:
                payload = st.state
                import json
                attr_payload = json.dumps(dict(st.attributes))
        try:
            await hass.services.async_call(
                "mqtt", "publish",
                {"topic": f"{topic_base}/state", "payload": payload, "retain": True},
                blocking=True,
            )
            await hass.services.async_call(
                "mqtt", "publish",
                {"topic": f"{topic_base}/attributes", "payload": attr_payload, "retain": True},
                blocking=True,
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Bridge MQTT publish failed for %s: %s", entity_id, exc)

    async def _publish_all(clear: bool = False) -> None:
        for eid in _BRIDGE_ENTITIES:
            await _publish_one(eid, clear=clear)
            await asyncio.sleep(0)  # yield to event loop between publishes

    # ── State-change publish ──────────────────────────────────────────────────
    @callback
    def _on_entity_change(event: Event) -> None:
        if not _bridge_enabled():
            return
        new = event.data.get("new_state")
        if new is None or new.state in ("unknown", "unavailable", "none"):
            return
        entity_id = event.data["entity_id"]
        hass.async_create_task(_publish_one(entity_id))

    unsubs.append(
        async_track_state_change_event(hass, _BRIDGE_ENTITIES, _on_entity_change)
    )

    # ── Initial publish on HA start ──────────────────────────────────────────
    @callback
    def _on_ha_start(event: Event) -> None:
        if not _bridge_enabled():
            return
        hass.async_create_task(_initial_publish())

    async def _initial_publish() -> None:
        await _publish_all()
        prefix = _prefix()
        await hass.services.async_call(
            "persistent_notification", "create",
            {
                "notification_id": "hph_bridge",
                "title": "HeatPump Hero — bridge active",
                "message": f"Multi-platform bridge published the initial snapshot to MQTT under prefix `{prefix}`.",
            },
            blocking=True,
        )

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _on_ha_start)

    # ── Bridge switch state change ───────────────────────────────────────────
    @callback
    def _on_bridge_switch(event: Event) -> None:
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        if old is None or new is None:
            return
        if old.state == "off" and new.state == "on":
            hass.async_create_task(_initial_publish())
        elif old.state == "on" and new.state == "off":
            hass.async_create_task(_disable_bridge())

    async def _disable_bridge() -> None:
        await _publish_all(clear=True)
        prefix = _prefix()
        await hass.services.async_call(
            "persistent_notification", "dismiss",
            {"notification_id": "hph_bridge"},
            blocking=True,
        )
        await hass.services.async_call(
            "persistent_notification", "create",
            {
                "notification_id": "hph_bridge",
                "title": "HeatPump Hero — bridge disabled",
                "message": f"Multi-platform bridge stopped. Retained MQTT topics under prefix `{prefix}` were cleared.",
            },
            blocking=True,
        )

    unsubs.append(
        async_track_state_change_event(
            hass, ["switch.hph_bridge_enabled"], _on_bridge_switch
        )
    )

    _LOGGER.debug("HPH bridge coordinator started")
    return unsubs
