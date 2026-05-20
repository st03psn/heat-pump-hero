"""HeatPump Hero — select platform.

Replaces v0.8 input_select helpers. Additionally registers typed-facade
proxy selects (CTRL_FACADES) that forward to the native vendor select
configured via the matching text.hph_ctrl_write_* helper.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CTRL_FACADES, DOMAIN, INTEGRATION_NAME, SELECT_HELPERS
from .helpers.proxy import FacadeProxyMixin, call_domain_service


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities: list[SelectEntity] = [
        HphSelect(unique_id, cfg) for unique_id, cfg in SELECT_HELPERS.items()
    ]
    for unique_id, cfg in CTRL_FACADES.items():
        if cfg.get("platform") == "select":
            entities.append(HphFacadeSelect(hass, unique_id, cfg))
    async_add_entities(entities)


class HphSelect(SelectEntity, RestoreEntity):
    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, unique_id: str, cfg: dict[str, Any]) -> None:
        self._attr_unique_id = unique_id
        self.entity_id = f"select.{unique_id}"
        self._attr_icon = cfg.get("icon")
        self._attr_options = list(cfg.get("options", []))
        self._initial = cfg.get("initial", self._attr_options[0] if self._attr_options else "")
        self._attr_current_option: str | None = self._initial
        # Enable HA frontend state translations (entity.select.<unique_id>.state.*)
        self._attr_translation_key = unique_id

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if (
            last_state is not None
            and last_state.state in self._attr_options
            and last_state.state not in (None, "unknown", "unavailable")
        ):
            self._attr_current_option = last_state.state
        else:
            self._attr_current_option = self._initial

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            return
        self._attr_current_option = option
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": INTEGRATION_NAME,
            "manufacturer": "HeatPump Hero",
            "model": "Bundle integration",
        }


class HphFacadeSelect(FacadeProxyMixin, SelectEntity):
    """Proxy select: reads from / writes to a vendor select via writer helper."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_assumed_state = False

    def __init__(self, hass: HomeAssistant, unique_id: str, cfg: dict[str, Any]) -> None:
        self.hass = hass
        self._attr_unique_id = unique_id
        self.entity_id = f"select.{unique_id}"
        self._attr_name = cfg.get("name", unique_id)
        self._attr_icon = cfg.get("icon")
        self._writer_id = f"text.{cfg['writer']}"
        self._fallback_options: list[str] = list(cfg.get("options", []))
        self._attr_options = list(self._fallback_options)
        self._attr_current_option: str | None = None
        self._attr_available = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._proxy_setup()

    async def async_will_remove_from_hass(self) -> None:
        await self._proxy_teardown()

    def _on_target_state(self, state) -> None:
        if state is None or state.state in ("unknown", "unavailable", "none", ""):
            self._attr_available = False
            self._attr_current_option = None
            return
        # Prefer native options from the target if present, else fallback.
        opts = state.attributes.get("options")
        if isinstance(opts, (list, tuple)) and opts:
            self._attr_options = [str(o) for o in opts]
        else:
            self._attr_options = list(self._fallback_options)
        self._attr_available = True
        self._attr_current_option = state.state if state.state in self._attr_options else state.state

    async def async_select_option(self, option: str) -> None:
        target = self._target_entity_id()
        if not target:
            return
        await call_domain_service(self.hass, target, "select_option", option)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": INTEGRATION_NAME,
            "manufacturer": "HeatPump Hero",
            "model": "Bundle integration",
        }
