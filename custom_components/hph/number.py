"""HeatPump Hero — number platform.

Replaces v0.8 input_number helpers (and exposes counter helpers as
restore-numbers; the cycle/event automations that increment them
will be ported to coordinators in phase 3). Additionally registers
typed-facade proxy numbers (CTRL_FACADES) that forward to the native
vendor number configured via the matching text.hph_ctrl_write_* helper.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import COUNTER_HELPERS, CTRL_FACADES, DOMAIN, INTEGRATION_NAME, NUMBER_HELPERS
from .helpers.proxy import FacadeProxyMixin, call_domain_service


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities: list[NumberEntity] = []
    for unique_id, cfg in NUMBER_HELPERS.items():
        entities.append(HphNumber(unique_id, cfg))
    for unique_id, cfg in COUNTER_HELPERS.items():
        merged = {
            "name": cfg.get("name", unique_id),
            "icon": cfg.get("icon", "mdi:counter"),
            "min": 0,
            "max": 999999,
            "step": 1,
            "initial": cfg.get("initial", 0),
        }
        entities.append(HphNumber(unique_id, merged))
    for unique_id, cfg in CTRL_FACADES.items():
        if cfg.get("platform") == "number":
            entities.append(HphFacadeNumber(hass, unique_id, cfg))
    async_add_entities(entities)


class HphNumber(NumberEntity, RestoreEntity):
    """A user-editable number helper, persisted across HA restarts."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_mode = NumberMode.AUTO

    def __init__(self, unique_id: str, cfg: dict[str, Any]) -> None:
        self._attr_unique_id = unique_id
        self.entity_id = f"number.{unique_id}"
        self._attr_name = cfg.get("name", unique_id)
        self._attr_icon = cfg.get("icon")
        self._attr_native_min_value = float(cfg.get("min", 0))
        self._attr_native_max_value = float(cfg.get("max", 100))
        self._attr_native_step = float(cfg.get("step", 1))
        if "unit_of_measurement" in cfg:
            self._attr_native_unit_of_measurement = cfg["unit_of_measurement"]
        self._initial = float(cfg.get("initial", 0))
        self._attr_native_value: float = self._initial

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._attr_native_value = float(last_state.state)
            except (TypeError, ValueError):
                self._attr_native_value = self._initial
        else:
            self._attr_native_value = self._initial

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = float(value)
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": INTEGRATION_NAME,
            "manufacturer": "HeatPump Hero",
            "model": "Bundle integration",
        }


class HphFacadeNumber(FacadeProxyMixin, NumberEntity):
    """Proxy number: reads from / writes to a vendor number via writer helper."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_mode = NumberMode.AUTO
    _attr_assumed_state = False

    def __init__(self, hass: HomeAssistant, unique_id: str, cfg: dict[str, Any]) -> None:
        self.hass = hass
        self._attr_unique_id = unique_id
        self.entity_id = f"number.{unique_id}"
        self._attr_name = cfg.get("name", unique_id)
        self._attr_icon = cfg.get("icon")
        self._writer_id = f"text.{cfg['writer']}"
        self._fallback_min = float(cfg.get("min", 0))
        self._fallback_max = float(cfg.get("max", 100))
        self._fallback_step = float(cfg.get("step", 1))
        self._fallback_unit = cfg.get("unit_of_measurement")
        self._attr_native_min_value = self._fallback_min
        self._attr_native_max_value = self._fallback_max
        self._attr_native_step = self._fallback_step
        if self._fallback_unit is not None:
            self._attr_native_unit_of_measurement = self._fallback_unit
        self._attr_native_value: float | None = None
        self._attr_available = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._proxy_setup()

    async def async_will_remove_from_hass(self) -> None:
        await self._proxy_teardown()

    def _on_target_state(self, state) -> None:
        if state is None or state.state in ("unknown", "unavailable", "none", ""):
            self._attr_available = False
            self._attr_native_value = None
            return
        # Inherit range/unit/step from target attributes when available.
        attrs = state.attributes
        try:
            self._attr_native_min_value = float(attrs.get("min", self._fallback_min))
            self._attr_native_max_value = float(attrs.get("max", self._fallback_max))
            self._attr_native_step = float(attrs.get("step", self._fallback_step))
        except (TypeError, ValueError):
            pass
        unit = attrs.get("unit_of_measurement", self._fallback_unit)
        if unit is not None:
            self._attr_native_unit_of_measurement = unit
        try:
            self._attr_native_value = float(state.state)
            self._attr_available = True
        except (TypeError, ValueError):
            self._attr_available = False
            self._attr_native_value = None

    async def async_set_native_value(self, value: float) -> None:
        target = self._target_entity_id()
        if not target:
            return
        await call_domain_service(self.hass, target, "set_value", float(value))

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": INTEGRATION_NAME,
            "manufacturer": "HeatPump Hero",
            "model": "Bundle integration",
        }
