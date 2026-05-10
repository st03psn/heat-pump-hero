"""HeatPump Hero — sensor platform.

Phase 2: programmatic registration of every `sensor.hph_*` entity
that previously lived as a `template:` block in the v0.8 YAML
packages. The Jinja templates themselves are bundled inside the
integration (`custom_components/hph/data/sensor_templates.yaml`) and
rendered at runtime by a generic `HphTemplateSensor` class.

This is NOT a YAML deploy — the user's `<config>/packages/` is no
longer the home of these definitions. The integration is the single
source of truth.

Future refactor (post v1.0, performance pass): rewrite the most
hot-path sensors as fully-native Python classes. The template-driven
approach is deliberately conservative for v0.9 to keep
regression-risk low while delivering all v0.8 behaviour 1:1.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    TrackTemplate,
    async_track_template_result,
)
from homeassistant.helpers.template import Template

from .const import DOMAIN, INTEGRATION_NAME

_LOGGER = logging.getLogger(__name__)
_DATA_FILE = Path(__file__).parent / "data" / "sensor_templates.yaml"


def _load_definitions() -> list[dict[str, Any]]:
    if not _DATA_FILE.is_file():
        _LOGGER.warning("Sensor template file missing: %s", _DATA_FILE)
        return []
    raw = yaml.safe_load(_DATA_FILE.read_text(encoding="utf-8")) or {}
    return list(raw.get("sensors", []) or [])


_DEVICE_CLASS_MAP = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "power": SensorDeviceClass.POWER,
    "energy": SensorDeviceClass.ENERGY,
    "frequency": SensorDeviceClass.FREQUENCY,
    "pressure": SensorDeviceClass.PRESSURE,
    "duration": SensorDeviceClass.DURATION,
    "current": SensorDeviceClass.CURRENT,
    "voltage": SensorDeviceClass.VOLTAGE,
}

_STATE_CLASS_MAP = {
    "measurement": SensorStateClass.MEASUREMENT,
    "total": SensorStateClass.TOTAL,
    "total_increasing": SensorStateClass.TOTAL_INCREASING,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    defs = await hass.async_add_executor_job(_load_definitions)
    if not defs:
        _LOGGER.error("No sensor definitions loaded from %s", _DATA_FILE)
        return
    entities = [HphTemplateSensor(hass, d) for d in defs]
    async_add_entities(entities)
    _LOGGER.info("HeatPump Hero registered %d template sensors", len(entities))


class HphTemplateSensor(SensorEntity):
    """A sensor whose state / availability / attributes come from Jinja
    templates loaded out of the integration's bundled data file.
    """

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, definition: dict[str, Any]) -> None:
        self.hass = hass
        self._def = definition

        unique_id = definition.get("unique_id") or definition.get("name", "")
        self._attr_unique_id = unique_id
        self.entity_id = f"sensor.{unique_id}"
        self._attr_name = definition.get("name", unique_id)
        self._attr_icon = definition.get("icon")

        unit = definition.get("unit_of_measurement")
        if unit:
            self._attr_native_unit_of_measurement = unit

        dc = definition.get("device_class")
        if dc and dc in _DEVICE_CLASS_MAP:
            self._attr_device_class = _DEVICE_CLASS_MAP[dc]

        sc = definition.get("state_class")
        if sc and sc in _STATE_CLASS_MAP:
            self._attr_state_class = _STATE_CLASS_MAP[sc]

        # Compile templates
        self._state_tpl: Template | None = None
        self._availability_tpl: Template | None = None
        self._attribute_tpls: dict[str, Template] = {}

        if "state" in definition:
            self._state_tpl = Template(str(definition["state"]), hass)
        if "availability" in definition:
            self._availability_tpl = Template(str(definition["availability"]), hass)
        for attr_key, attr_tpl in (definition.get("attributes") or {}).items():
            self._attribute_tpls[attr_key] = Template(str(attr_tpl), hass)

        # Working state — starts unavailable until the first template
        # evaluation completes. This prevents the utility_meter from seeing
        # a spurious near-zero reading during integration reload (which
        # would be interpreted as a meter reset and zero the daily counter).
        self._raw_state: Any = None
        self._raw_available: bool = False
        self._initialized: bool = False
        self._raw_attrs: dict[str, Any] = {}
        self._cancel_listeners: list = []

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        track_specs: list[TrackTemplate] = []
        if self._state_tpl is not None:
            track_specs.append(TrackTemplate(self._state_tpl, None))
        if self._availability_tpl is not None:
            track_specs.append(TrackTemplate(self._availability_tpl, None))
        for tpl in self._attribute_tpls.values():
            track_specs.append(TrackTemplate(tpl, None))

        if not track_specs:
            return

        info = async_track_template_result(
            self.hass, track_specs, self._on_template_change
        )
        self.async_on_remove(info.async_remove)
        info.async_refresh()

    @callback
    def _on_template_change(self, event, updates):
        for upd in updates:
            tpl = upd.template
            result = upd.result
            if tpl is self._state_tpl:
                self._raw_state = result
            elif tpl is self._availability_tpl:
                self._raw_available = bool(result) if not isinstance(result, Exception) else False
            else:
                # Find which attribute key
                for key, atpl in self._attribute_tpls.items():
                    if atpl is tpl:
                        self._raw_attrs[key] = result
                        break
        # Mark as initialised after the first evaluation so that available
        # returns a meaningful value (not forced-unavailable).
        self._initialized = True
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        if not self._initialized:
            return False
        if self._availability_tpl is None:
            return True
        return bool(self._raw_available)

    @property
    def native_value(self) -> Any:
        if isinstance(self._raw_state, Exception):
            return None
        if isinstance(self._raw_state, str):
            stripped = self._raw_state.strip()
            if stripped in (STATE_UNKNOWN, STATE_UNAVAILABLE, "None", "none", ""):
                return None
            return stripped
        return self._raw_state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, val in self._raw_attrs.items():
            if isinstance(val, Exception):
                continue
            if isinstance(val, str):
                out[key] = val.strip()
            else:
                out[key] = val
        return out

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "hub")},
            "name": INTEGRATION_NAME,
            "manufacturer": "HeatPump Hero",
            "model": "Bundle integration",
        }
