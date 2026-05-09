"""Config flow for HeatPump Hero — 4-step wizard.

Step 1 (user)        — vendor preset selection
Step 2 (model)       — pump model selection
Step 3 (sensors)     — optional external sensors (entity selectors)
Step 4 (confirm)     — final confirmation + restart hint

Options flow re-runs the same wizard from the integration's
"Configure" button so users can change settings later.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, INTEGRATION_NAME, PUMP_MODELS, VENDOR_PRESETS

_LOGGER = logging.getLogger(__name__)


def _vendor_options() -> list[selector.SelectOptionDict]:
    return [
        selector.SelectOptionDict(value=v, label=v.replace("_", " ").title())
        for v in list(VENDOR_PRESETS.keys()) + ["keep_current"]
    ]


def _model_options() -> list[selector.SelectOptionDict]:
    return [
        selector.SelectOptionDict(value=k, label=v.get("description", k))
        for k, v in PUMP_MODELS.items()
    ]


def _temp_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor",
            device_class=SensorDeviceClass.TEMPERATURE,
            multiple=False,
        )
    )


def _power_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor",
            device_class=SensorDeviceClass.POWER,
            multiple=False,
        )
    )


def _energy_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor",
            device_class=SensorDeviceClass.ENERGY,
            multiple=False,
        )
    )


class HphConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for HeatPump Hero."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Step 1 — pick a vendor preset."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            self._data["vendor_preset"] = user_input["vendor_preset"]
            return await self.async_step_model()

        schema = vol.Schema(
            {
                vol.Required("vendor_preset", default="panasonic_heishamon"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_vendor_options(),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={"name": INTEGRATION_NAME},
        )

    async def async_step_model(self, user_input: dict[str, Any] | None = None) -> Any:
        """Step 2 — pick the heat-pump model."""
        if user_input is not None:
            self._data["pump_model"] = user_input["pump_model"]
            return await self.async_step_sensors()

        schema = vol.Schema(
            {
                vol.Required("pump_model", default="panasonic_l_aql"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_model_options(),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="model", data_schema=schema)

    async def async_step_sensors(self, user_input: dict[str, Any] | None = None) -> Any:
        """Step 3 — optional external sensors."""
        if user_input is not None:
            self._data.update(
                {
                    "indoor_temp_entity": user_input.get("indoor_temp_entity", ""),
                    "outdoor_temp_entity": user_input.get("outdoor_temp_entity", ""),
                    "external_thermal_power": user_input.get("external_thermal_power", ""),
                    "external_electrical_power": user_input.get("external_electrical_power", ""),
                    "external_thermal_energy": user_input.get("external_thermal_energy", ""),
                    "external_electrical_energy": user_input.get("external_electrical_energy", ""),
                }
            )
            return await self.async_step_confirm()

        schema = vol.Schema(
            {
                vol.Optional("indoor_temp_entity"): _temp_selector(),
                vol.Optional("outdoor_temp_entity"): _temp_selector(),
                vol.Optional("external_thermal_power"): _power_selector(),
                vol.Optional("external_electrical_power"): _power_selector(),
                vol.Optional("external_thermal_energy"): _energy_selector(),
                vol.Optional("external_electrical_energy"): _energy_selector(),
            }
        )
        return self.async_show_form(step_id="sensors", data_schema=schema)

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> Any:
        """Step 4 — confirm + create entry."""
        if user_input is not None:
            return self.async_create_entry(title=INTEGRATION_NAME, data=self._data)

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "vendor": self._data.get("vendor_preset", "?"),
                "model": self._data.get("pump_model", "?"),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "HphOptionsFlow":
        return HphOptionsFlow()


class HphOptionsFlow(config_entries.OptionsFlow):
    """Full 3-step reconfigure wizard (vendor → sensors → done)."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        # config_entry is injected by HA after construction.
        if not self._data:
            self._data = dict(self.config_entry.data)

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_sensors()

        schema = vol.Schema(
            {
                vol.Required(
                    "vendor_preset", default=self._data.get("vendor_preset", "keep_current")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_vendor_options(),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    "pump_model", default=self._data.get("pump_model", "panasonic_l_aql")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_model_options(),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_sensors(self, user_input: dict[str, Any] | None = None) -> Any:
        """Step 2 — reconfigure optional external sensors."""
        if user_input is not None:
            self._data.update(
                {
                    "indoor_temp_entity": user_input.get("indoor_temp_entity", ""),
                    "outdoor_temp_entity": user_input.get("outdoor_temp_entity", ""),
                    "external_thermal_power": user_input.get("external_thermal_power", ""),
                    "external_electrical_power": user_input.get("external_electrical_power", ""),
                    "external_thermal_energy": user_input.get("external_thermal_energy", ""),
                    "external_electrical_energy": user_input.get("external_electrical_energy", ""),
                }
            )
            return self.async_create_entry(title="", data=self._data)

        schema = vol.Schema(
            {
                vol.Optional(
                    "indoor_temp_entity",
                    default=self._data.get("indoor_temp_entity", ""),
                ): _temp_selector(),
                vol.Optional(
                    "outdoor_temp_entity",
                    default=self._data.get("outdoor_temp_entity", ""),
                ): _temp_selector(),
                vol.Optional(
                    "external_thermal_power",
                    default=self._data.get("external_thermal_power", ""),
                ): _power_selector(),
                vol.Optional(
                    "external_electrical_power",
                    default=self._data.get("external_electrical_power", ""),
                ): _power_selector(),
                vol.Optional(
                    "external_thermal_energy",
                    default=self._data.get("external_thermal_energy", ""),
                ): _energy_selector(),
                vol.Optional(
                    "external_electrical_energy",
                    default=self._data.get("external_electrical_energy", ""),
                ): _energy_selector(),
            }
        )
        return self.async_show_form(step_id="sensors", data_schema=schema)
