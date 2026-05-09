"""HeatPump Hero — switch platform.

Replaces v0.8 input_boolean helpers.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, INTEGRATION_NAME, SWITCH_HELPERS


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities = [HphSwitch(unique_id, cfg) for unique_id, cfg in SWITCH_HELPERS.items()]
    async_add_entities(entities)


class HphSwitch(SwitchEntity, RestoreEntity):
    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, unique_id: str, cfg: dict[str, Any]) -> None:
        self._attr_unique_id = unique_id
        self.entity_id = f"switch.{unique_id}"
        self._attr_name = cfg.get("name", unique_id)
        self._attr_icon = cfg.get("icon")
        self._initial = bool(cfg.get("initial", False))
        self._attr_is_on: bool = self._initial

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in ("on", "off"):
            self._attr_is_on = last_state.state == "on"
        else:
            self._attr_is_on = self._initial

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": INTEGRATION_NAME,
            "manufacturer": "HeatPump Hero",
            "model": "Bundle integration",
        }
