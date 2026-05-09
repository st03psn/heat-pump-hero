"""HeatPump Hero — datetime platform.

Replaces v0.8 input_datetime helpers (those configured with both
date and time — that's all of ours).
"""

from __future__ import annotations

from datetime import datetime as dt
from typing import Any

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import DATETIME_HELPERS, DOMAIN, INTEGRATION_NAME


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities = [HphDateTime(unique_id, cfg) for unique_id, cfg in DATETIME_HELPERS.items()]
    async_add_entities(entities)


class HphDateTime(DateTimeEntity, RestoreEntity):
    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, unique_id: str, cfg: dict[str, Any]) -> None:
        self._attr_unique_id = unique_id
        self.entity_id = f"datetime.{unique_id}"
        self._attr_name = cfg.get("name", unique_id)
        self._attr_icon = cfg.get("icon")
        self._attr_native_value: dt | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable", ""):
            try:
                self._attr_native_value = dt_util.parse_datetime(last_state.state)
            except Exception:  # noqa: BLE001 — bad state, fall through to None
                self._attr_native_value = None

    async def async_set_value(self, value: dt) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": INTEGRATION_NAME,
            "manufacturer": "HeatPump Hero",
            "model": "Bundle integration",
        }
