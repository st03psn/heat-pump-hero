"""HeatPump Hero — binary_sensor platform.

Same template-driven approach as sensor.py. Loads
`data/binary_sensor_templates.yaml` and instantiates one entity per
template definition.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    TrackTemplate,
    async_track_template_result,
)
from homeassistant.helpers.template import Template

from .const import DOMAIN, INTEGRATION_NAME

_LOGGER = logging.getLogger(__name__)
_DATA_FILE = Path(__file__).parent / "data" / "binary_sensor_templates.yaml"


def _load_definitions() -> list[dict[str, Any]]:
    if not _DATA_FILE.is_file():
        _LOGGER.warning("Binary-sensor template file missing: %s", _DATA_FILE)
        return []
    raw = yaml.safe_load(_DATA_FILE.read_text(encoding="utf-8")) or {}
    return list(raw.get("binary_sensors", []) or [])


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    defs = _load_definitions()
    if not defs:
        _LOGGER.error("No binary-sensor definitions loaded")
        return
    entities = [HphTemplateBinarySensor(hass, d) for d in defs]
    async_add_entities(entities)
    _LOGGER.info("HeatPump Hero registered %d template binary_sensors", len(entities))


class HphTemplateBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, definition: dict[str, Any]) -> None:
        self.hass = hass
        self._def = definition

        unique_id = definition.get("unique_id") or definition.get("name", "")
        self._attr_unique_id = unique_id
        self.entity_id = f"binary_sensor.{unique_id}"
        self._attr_name = definition.get("name", unique_id)
        self._attr_icon = definition.get("icon")

        if "device_class" in definition:
            try:
                from homeassistant.components.binary_sensor import BinarySensorDeviceClass

                self._attr_device_class = BinarySensorDeviceClass(definition["device_class"])
            except Exception:  # noqa: BLE001
                pass

        self._state_tpl: Template | None = None
        self._availability_tpl: Template | None = None
        self._attribute_tpls: dict[str, Template] = {}

        if "state" in definition:
            self._state_tpl = Template(str(definition["state"]), hass)
        if "availability" in definition:
            self._availability_tpl = Template(str(definition["availability"]), hass)
        for k, v in (definition.get("attributes") or {}).items():
            self._attribute_tpls[k] = Template(str(v), hass)

        self._raw_is_on: bool | None = None
        self._raw_available: bool = True
        self._raw_attrs: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        specs: list[TrackTemplate] = []
        if self._state_tpl is not None:
            specs.append(TrackTemplate(self._state_tpl, None))
        if self._availability_tpl is not None:
            specs.append(TrackTemplate(self._availability_tpl, None))
        for tpl in self._attribute_tpls.values():
            specs.append(TrackTemplate(tpl, None))
        if not specs:
            return
        info = async_track_template_result(self.hass, specs, self._on_template_change)
        self.async_on_remove(info.async_remove)
        info.async_refresh()

    @callback
    def _on_template_change(self, event, updates):
        for upd in updates:
            tpl = upd.template
            result = upd.result
            if tpl is self._state_tpl:
                self._raw_is_on = self._coerce_bool(result)
            elif tpl is self._availability_tpl:
                self._raw_available = bool(result) if not isinstance(result, Exception) else False
            else:
                for k, atpl in self._attribute_tpls.items():
                    if atpl is tpl:
                        self._raw_attrs[k] = result
                        break
        self.async_write_ha_state()

    @staticmethod
    def _coerce_bool(value: Any) -> bool | None:
        if isinstance(value, Exception):
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ("true", "on", "yes", "1"):
                return True
            if v in ("false", "off", "no", "0"):
                return False
            return None
        return bool(value)

    @property
    def is_on(self) -> bool | None:
        return self._raw_is_on

    @property
    def available(self) -> bool:
        if self._availability_tpl is None:
            return super().available
        return bool(self._raw_available)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            k: (v.strip() if isinstance(v, str) else v)
            for k, v in self._raw_attrs.items()
            if not isinstance(v, Exception)
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": INTEGRATION_NAME,
            "manufacturer": "HeatPump Hero",
            "model": "Bundle integration",
        }
