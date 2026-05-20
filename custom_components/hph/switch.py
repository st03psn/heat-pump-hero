"""HeatPump Hero — switch platform.

Replaces v0.8 input_boolean helpers. Additionally registers typed-facade
proxy switches (CTRL_FACADES) that forward to the native vendor switch
configured via the matching text.hph_ctrl_write_* helper.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CTRL_FACADES, DOMAIN, INTEGRATION_NAME, SWITCH_HELPERS
from .helpers.proxy import FacadeProxyMixin, call_domain_service


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities: list[SwitchEntity] = [
        HphSwitch(unique_id, cfg) for unique_id, cfg in SWITCH_HELPERS.items()
    ]
    for unique_id, cfg in CTRL_FACADES.items():
        if cfg.get("platform") == "switch":
            entities.append(HphFacadeSwitch(hass, unique_id, cfg))
    async_add_entities(entities)


class HphSwitch(SwitchEntity, RestoreEntity):
    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, unique_id: str, cfg: dict[str, Any]) -> None:
        self._attr_unique_id = unique_id
        self.entity_id = f"switch.{unique_id}"
        self._attr_translation_key = unique_id
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


class HphFacadeSwitch(FacadeProxyMixin, SwitchEntity):
    """Proxy switch: target may be switch.* or select.* with on/off options."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_assumed_state = False

    def __init__(self, hass: HomeAssistant, unique_id: str, cfg: dict[str, Any]) -> None:
        self.hass = hass
        self._attr_unique_id = unique_id
        self.entity_id = f"switch.{unique_id}"
        self._attr_name = cfg.get("name", unique_id)
        self._attr_icon = cfg.get("icon")
        self._writer_id = f"text.{cfg['writer']}"
        self._attr_is_on: bool = False
        self._attr_available = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._proxy_setup()

    async def async_will_remove_from_hass(self) -> None:
        await self._proxy_teardown()

    def _on_target_state(self, state) -> None:
        if state is None or state.state in ("unknown", "unavailable", "none", ""):
            self._attr_available = False
            self._attr_is_on = False
            return
        self._attr_available = True
        s = str(state.state).lower()
        self._attr_is_on = s in ("on", "true", "1", "heat", "active", "enabled")

    async def async_turn_on(self, **kwargs: Any) -> None:
        target = self._target_entity_id()
        if not target:
            return
        await call_domain_service(self.hass, target, "turn_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        target = self._target_entity_id()
        if not target:
            return
        await call_domain_service(self.hass, target, "turn_off")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": INTEGRATION_NAME,
            "manufacturer": "HeatPump Hero",
            "model": "Bundle integration",
        }
