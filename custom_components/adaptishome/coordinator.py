"""Опитування хаба: знімки обраних об'єктів раз на 30 с, нові події — на шину HA."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AdaptisHomeApi, AuthError, HubError
from .const import DOMAIN, EVENT, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AdaptisHomeCoordinator(DataUpdateCoordinator[dict[str, dict]]):
    """data: {id об'єкта: знімок /api/device}."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: AdaptisHomeApi, objects: list[str]) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api, self.objects = api, objects
        self._last_event: dict[str, int] = {}     # id об'єкта → час останньої події, яку вже віддали на шину

    async def _async_update_data(self) -> dict[str, dict]:
        out = {}
        for dev_id in self.objects:
            try:
                out[dev_id] = await self.api.device(dev_id)
            except AuthError as e:
                raise ConfigEntryAuthFailed(str(e)) from e
            except HubError as e:
                raise UpdateFailed(str(e)) from e
            self._fire_new_events(dev_id, out[dev_id])
        return out

    def _fire_new_events(self, dev_id: str, snap: dict) -> None:
        events = snap.get("events") or []
        if not events: return
        if dev_id not in self._last_event:            # перше опитування: лише запам'ятати, старе не переказувати
            self._last_event[dev_id] = events[0]["ts"]
            return
        ch = {c["id"]: c["name"] for c in snap.get("channels", [])}
        for e in sorted((e for e in events if e["ts"] > self._last_event[dev_id]), key=lambda e: e["ts"]):
            self.hass.bus.async_fire(EVENT, {"object_id": dev_id, "object": snap.get("name"), "kind": e["kind"], "ts": e["ts"],
                                             "to": ch.get(e.get("to"), e.get("to")),
                                             "from": [ch.get(x, x) for x in e.get("from", [])]})
            self._last_event[dev_id] = e["ts"]
