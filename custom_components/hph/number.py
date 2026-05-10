"""HeatPump Hero — number platform.

Replaces v0.8 input_number helpers (and exposes counter helpers as
restore-numbers; the cycle/event automations that increment them
will be ported to coordinators in phase 3).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import COUNTER_HELPERS, DOMAIN, INTEGRATION_NAME, NUMBER_HELPERS


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities: list[NumberEntity] = []
    for unique_id, cfg in NUMBER_HELPERS.items():
        entities.append(HphNumber(unique_id, cfg))
    for unique_id, cfg in COUNTER_HELPERS.items():
        # Counters are exposed as numbers with min=0, step=1.
        merged = {
            "name": cfg.get("name", unique_id),
            "icon": cfg.get("icon", "mdi:counter"),
            "min": 0,
            "max": 999999,
            "step": 1,
            "initial": cfg.get("initial", 0),
        }
        entities.append(HphNumber(unique_id, merged))
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
