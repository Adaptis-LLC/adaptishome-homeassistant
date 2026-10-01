"""Спільне для сутностей: один пристрій HA на об'єкт AdaptisHome."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AdaptisHomeCoordinator


class AdaptisHomeEntity(CoordinatorEntity[AdaptisHomeCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AdaptisHomeCoordinator, dev_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.dev_id = dev_id
        self._attr_unique_id = f"{dev_id}_{key}"
        self._attr_translation_key = key

    @property
    def snap(self) -> dict:
        return self.coordinator.data.get(self.dev_id) or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self.snap)

    @property
    def device_info(self) -> DeviceInfo:
        s, d = self.snap, self.snap.get("device") or {}
        return DeviceInfo(identifiers={(DOMAIN, self.dev_id)}, name=s.get("name") or self.dev_id, manufacturer="Adaptis",
                          model=d.get("model") or "MikroTik", serial_number=d.get("serial"),
                          sw_version=f"config v{d['config_version']}" if d.get("config_version") else None,
                          configuration_url=f"{self.coordinator.api.hub}/?id={self.dev_id}")


class AdaptisHomeChannelEntity(AdaptisHomeEntity):
    """Сутність одного каналу: назва каналу з хаба стає частиною імені."""

    def __init__(self, coordinator: AdaptisHomeCoordinator, dev_id: str, ch_id: str, key: str) -> None:
        super().__init__(coordinator, dev_id, f"{ch_id}_{key}")
        self.ch_id = ch_id
        self._attr_translation_key = f"channel_{key}"

    @property
    def channel(self) -> dict:
        return next((c for c in self.snap.get("channels", []) if c["id"] == self.ch_id), {})

    @property
    def translation_placeholders(self) -> dict[str, str]:
        return {"channel": self.channel.get("name") or self.ch_id}

    @property
    def available(self) -> bool:
        return super().available and bool(self.channel)
