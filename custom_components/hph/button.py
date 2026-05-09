"""HeatPump Hero — button platform.

Manual triggers + counter resets. Service routing is best-effort —
the actual service handlers will land in coordinators (phase 3).
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BUTTON_DEFS, DOMAIN, INTEGRATION_NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities = [HphButton(hass, unique_id, cfg) for unique_id, cfg in BUTTON_DEFS.items()]
    async_add_entities(entities)


class HphButton(ButtonEntity):
    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, unique_id: str, cfg: dict[str, Any]) -> None:
        self.hass = hass
        self._attr_unique_id = unique_id
        self.entity_id = f"button.{unique_id}"
        self._attr_name = cfg.get("name", unique_id)
        self._attr_icon = cfg.get("icon")
        self._service = cfg.get("service")
        self._service_data = cfg.get("service_data", {})

    async def async_press(self) -> None:
        if not self._service:
            _LOGGER.debug("Button %s pressed but no service bound", self.unique_id)
            return
        if self._service == "reset_counter":
            # Special: reset a number-counter back to 0.
            target = self._service_data.get("counter")
            if target:
                await self.hass.services.async_call(
                    "number",
                    "set_value",
                    {"entity_id": f"number.{target}", "value": 0},
                    blocking=False,
                )
            return
        # Generic: call into the integration's own service domain.
        await self.hass.services.async_call(
            DOMAIN, self._service, self._service_data, blocking=False
        )

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": INTEGRATION_NAME,
            "manufacturer": "HeatPump Hero",
            "model": "Bundle integration",
        }
