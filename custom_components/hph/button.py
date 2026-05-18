"""HeatPump Hero — button platform.

Manual triggers + counter resets. Additionally registers typed-facade
proxy buttons (CTRL_FACADES) that press the native vendor button
configured via the matching text.hph_ctrl_write_* helper.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BUTTON_DEFS, CTRL_FACADES, DOMAIN, INTEGRATION_NAME
from .helpers.proxy import FacadeProxyMixin, call_domain_service

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities: list[ButtonEntity] = [
        HphButton(hass, unique_id, cfg) for unique_id, cfg in BUTTON_DEFS.items()
    ]
    for unique_id, cfg in CTRL_FACADES.items():
        if cfg.get("platform") == "button":
            entities.append(HphFacadeButton(hass, unique_id, cfg))
    async_add_entities(entities)


class HphButton(ButtonEntity):
    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

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
            target = self._service_data.get("counter")
            if target:
                await self.hass.services.async_call(
                    "number",
                    "set_value",
                    {"entity_id": f"number.{target}", "value": 0},
                    blocking=False,
                )
            return
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


class HphFacadeButton(FacadeProxyMixin, ButtonEntity):
    """Proxy button: presses a vendor button via writer helper."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, unique_id: str, cfg: dict[str, Any]) -> None:
        self.hass = hass
        self._attr_unique_id = unique_id
        self.entity_id = f"button.{unique_id}"
        self._attr_name = cfg.get("name", unique_id)
        self._attr_icon = cfg.get("icon")
        self._writer_id = f"text.{cfg['writer']}"
        self._attr_available = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._proxy_setup()

    async def async_will_remove_from_hass(self) -> None:
        await self._proxy_teardown()

    def _on_target_state(self, state) -> None:
        # Buttons report their last-pressed timestamp as state — being
        # "unavailable" still hides them. Otherwise available.
        if state is None or state.state == "unavailable":
            self._attr_available = False
            return
        self._attr_available = True

    async def async_press(self) -> None:
        target = self._target_entity_id()
        if not target:
            return
        await call_domain_service(self.hass, target, "press")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": INTEGRATION_NAME,
            "manufacturer": "HeatPump Hero",
            "model": "Bundle integration",
        }
