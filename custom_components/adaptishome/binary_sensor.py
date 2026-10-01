"""Бінарні датчики: об'єкт на зв'язку, інтернет через резерв; канал готовий."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AdaptisHomeEntry
from .entity import AdaptisHomeChannelEntity, AdaptisHomeEntity


async def async_setup_entry(hass: HomeAssistant, entry: AdaptisHomeEntry, add: AddEntitiesCallback) -> None:
    co = entry.runtime_data
    ents: list[BinarySensorEntity] = []
    for dev_id, snap in co.data.items():
        ents += [OnlineSensor(co, dev_id), FailoverSensor(co, dev_id)]
        ents += [ChannelReadySensor(co, dev_id, c["id"]) for c in snap.get("channels", [])]
    add(ents)


class OnlineSensor(AdaptisHomeEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, co, dev_id) -> None:
        super().__init__(co, dev_id, "online")

    @property
    def is_on(self) -> bool:
        return self.snap.get("status") in ("ok", "failover")


class FailoverSensor(AdaptisHomeEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, co, dev_id) -> None:
        super().__init__(co, dev_id, "failover")

    @property
    def is_on(self) -> bool:
        return self.snap.get("status") == "failover"


class ChannelReadySensor(AdaptisHomeChannelEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, co, dev_id, ch_id) -> None:
        super().__init__(co, dev_id, ch_id, "ready")

    @property
    def is_on(self) -> bool:
        return self.channel.get("state") in ("active", "ready")
