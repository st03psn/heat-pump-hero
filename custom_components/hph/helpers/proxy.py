"""Shared logic for typed-facade proxy entities.

A proxy entity (select.hph_*, switch.hph_*, number.hph_*, button.hph_*)
transparently forwards reads/writes to the native vendor entity whose
entity_id is stored in the matching text.hph_ctrl_write_* helper.

The mixin handles:
- Resolution of the writer helper -> target entity_id at each evaluation
- Re-subscription to state-change events when the writer value changes
- Availability gating: unavailable when writer is empty / target missing
- Domain-aware service dispatch on writes (target may be select/switch/
  input_boolean/number/button depending on what the vendor exposes)
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(__name__)

# Sentinel state values that mean "no usable reading from target".
_BAD_STATES = frozenset({"unknown", "unavailable", "none", "", None})


class FacadeProxyMixin:
    """Mix into a proxy entity to get writer-helper resolution and tracking.

    The subclass MUST set:
        self.hass         -> HomeAssistant
        self._writer_id   -> str, full entity_id of the writer helper
                              (e.g. "text.hph_ctrl_write_quiet_mode")
        self._on_target_state(state)  -> sync callback invoked whenever the
                              resolved target's state changes (or when the
                              target itself is re-resolved). State may be None
                              if target is missing.

    The subclass typically:
        - calls self._proxy_setup() inside async_added_to_hass()
        - reads self._target_entity_id() to know where to write
        - reads self._target_state() for the live state object
        - sets self._attr_available based on self._writer_id state + target state
    """

    hass: HomeAssistant
    _writer_id: str
    _unsub_writer: Callable[[], None] | None = None
    _unsub_target: Callable[[], None] | None = None
    _cached_target_id: str = ""

    def _resolved_target(self) -> str:
        """Read the writer helper's current value (= target entity_id)."""
        st = self.hass.states.get(self._writer_id)
        if st is None or st.state in _BAD_STATES:
            return ""
        return st.state

    def _target_state(self):
        """Current State of the resolved target, or None."""
        target = self._resolved_target()
        if not target:
            return None
        return self.hass.states.get(target)

    def _target_entity_id(self) -> str:
        return self._resolved_target()

    def _is_target_available(self) -> bool:
        st = self._target_state()
        return st is not None and st.state not in _BAD_STATES

    async def _proxy_setup(self) -> None:
        """Wire up writer-helper + target listeners. Call from async_added_to_hass."""
        # Subscribe to writer helper changes.
        self._unsub_writer = async_track_state_change_event(
            self.hass, [self._writer_id], self._writer_changed
        )
        # Subscribe to the currently resolved target.
        self._cached_target_id = self._resolved_target()
        self._attach_target_listener(self._cached_target_id)
        # Push initial state into the subclass AND commit it to HA's state machine.
        # Without async_write_ha_state() here the entity stays 'unavailable' after
        # a reload because _on_target_state only updates internal attrs — HA never
        # learns the resolved state until the next writer/target state-change event.
        self._on_target_state(self._target_state())  # type: ignore[attr-defined]
        if hasattr(self, "async_write_ha_state"):
            self.async_write_ha_state()

    def _attach_target_listener(self, target_id: str) -> None:
        if self._unsub_target is not None:
            self._unsub_target()
            self._unsub_target = None
        if target_id:
            self._unsub_target = async_track_state_change_event(
                self.hass, [target_id], self._target_changed
            )

    @callback
    def _writer_changed(self, event: Event) -> None:
        new_target = self._resolved_target()
        if new_target != self._cached_target_id:
            self._cached_target_id = new_target
            self._attach_target_listener(new_target)
        # Re-evaluate state regardless (writer state can become unavailable).
        self._on_target_state(self._target_state())  # type: ignore[attr-defined]
        if hasattr(self, "async_write_ha_state"):
            self.async_write_ha_state()

    @callback
    def _target_changed(self, event: Event) -> None:
        self._on_target_state(self._target_state())  # type: ignore[attr-defined]
        if hasattr(self, "async_write_ha_state"):
            self.async_write_ha_state()

    async def _proxy_teardown(self) -> None:
        if self._unsub_writer:
            self._unsub_writer()
            self._unsub_writer = None
        if self._unsub_target:
            self._unsub_target()
            self._unsub_target = None


async def call_domain_service(
    hass: HomeAssistant,
    target_entity_id: str,
    intent: str,
    value: Any = None,
) -> bool:
    """Dispatch a write to whichever domain the target entity lives in.

    intent is one of: "turn_on", "turn_off", "set_value", "select_option", "press".
    Returns True on success, False if no suitable mapping was found.
    """
    if not target_entity_id:
        return False
    domain = target_entity_id.split(".", 1)[0]

    if intent in ("turn_on", "turn_off"):
        # switch.* / input_boolean.* handle natively; for select.* assume on/off
        # are valid options.
        if domain in ("switch", "input_boolean"):
            await hass.services.async_call(
                domain, intent, {"entity_id": target_entity_id}, blocking=False
            )
            return True
        if domain == "select":
            opt = "on" if intent == "turn_on" else "off"
            await hass.services.async_call(
                "select", "select_option",
                {"entity_id": target_entity_id, "option": opt}, blocking=False
            )
            return True
        # Last resort: use homeassistant.toggle-style service
        await hass.services.async_call(
            "homeassistant", intent, {"entity_id": target_entity_id}, blocking=False
        )
        return True

    if intent == "set_value":
        if domain == "number":
            await hass.services.async_call(
                "number", "set_value",
                {"entity_id": target_entity_id, "value": value}, blocking=False
            )
            return True
        if domain == "input_number":
            await hass.services.async_call(
                "input_number", "set_value",
                {"entity_id": target_entity_id, "value": value}, blocking=False
            )
            return True
        _LOGGER.warning(
            "Cannot set numeric value on %s — unsupported domain '%s'",
            target_entity_id, domain,
        )
        return False

    if intent == "select_option":
        if domain == "select":
            await hass.services.async_call(
                "select", "select_option",
                {"entity_id": target_entity_id, "option": value}, blocking=False
            )
            return True
        if domain == "input_select":
            await hass.services.async_call(
                "input_select", "select_option",
                {"entity_id": target_entity_id, "option": value}, blocking=False
            )
            return True
        _LOGGER.warning(
            "Cannot select option on %s — unsupported domain '%s'",
            target_entity_id, domain,
        )
        return False

    if intent == "press":
        if domain == "button":
            await hass.services.async_call(
                "button", "press",
                {"entity_id": target_entity_id}, blocking=False
            )
            return True
        if domain == "input_button":
            await hass.services.async_call(
                "input_button", "press",
                {"entity_id": target_entity_id}, blocking=False
            )
            return True
        if domain == "script":
            await hass.services.async_call(
                "script", "turn_on",
                {"entity_id": target_entity_id}, blocking=False
            )
            return True
        _LOGGER.warning(
            "Cannot press %s — unsupported domain '%s'",
            target_entity_id, domain,
        )
        return False

    _LOGGER.warning("Unknown intent '%s' for %s", intent, target_entity_id)
    return False
