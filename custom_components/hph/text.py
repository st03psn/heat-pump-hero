"""HeatPump Hero — text platform.

Replaces v0.8 input_text helpers. All entity unique_ids match the
original YAML keys so entity_ids stay stable and recorder history
reconnects on the v0.8 → v0.9 migration.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, INTEGRATION_NAME, TEXT_HELPERS


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Register every helper from TEXT_HELPERS."""
    entities = [HphText(unique_id, cfg) for unique_id, cfg in TEXT_HELPERS.items()]
    async_add_entities(entities)


class HphText(TextEntity, RestoreEntity):
    """A user-editable text helper, persisted across HA restarts."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_mode = TextMode.TEXT

    def __init__(self, unique_id: str, cfg: dict[str, Any]) -> None:
        self._attr_unique_id = unique_id
        self.entity_id = f"text.{unique_id}"
        self._attr_name = cfg.get("name", unique_id)
        self._attr_icon = cfg.get("icon")
        self._attr_native_max = int(cfg.get("max", 255))
        self._attr_native_min = 0
        self._initial = cfg.get("initial", "")
        self._attr_native_value: str = self._initial

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            self._attr_native_value = last_state.state
        else:
            self._attr_native_value = self._initial

    async def async_set_value(self, value: str) -> None:
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
