"""Подія об'єкта: перемикання на резерв, повернення, перезавантаження, нова конфігурація — для автоматизацій і журналу."""
from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AdaptisHomeEntry
from .const import EVENT
from .entity import AdaptisHomeEntity


async def async_setup_entry(hass: HomeAssistant, entry: AdaptisHomeEntry, add: AddEntitiesCallback) -> None:
    add([ObjectEvent(entry.runtime_data, dev_id) for dev_id in entry.runtime_data.data])


class ObjectEvent(AdaptisHomeEntity, EventEntity):
    _attr_event_types = ["failover", "return", "boot", "config"]

    def __init__(self, co, dev_id) -> None:
        super().__init__(co, dev_id, "event")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.hass.bus.async_listen(EVENT, self._on_event))

    @callback
    def _on_event(self, ev: Event) -> None:
        if ev.data.get("object_id") != self.dev_id or ev.data.get("kind") not in self._attr_event_types: return
        self._trigger_event(ev.data["kind"], {k: ev.data.get(k) for k in ("to", "from", "ts")})
        self.async_write_ha_state()
