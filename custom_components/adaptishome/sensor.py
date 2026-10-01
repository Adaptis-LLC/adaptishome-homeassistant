"""Датчики: стан об'єкта, активний канал, затримка, швидкість, трафік, статистика; по каналах — стан, затримка, втрати, трафік."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfDataRate, UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AdaptisHomeEntry
from .entity import AdaptisHomeChannelEntity, AdaptisHomeEntity

STATUSES = ["ok", "failover", "offline", "new"]
CH_STATES = ["active", "ready", "waiting", "down", "disabled"]


@dataclass(frozen=True, kw_only=True)
class ObjDesc(SensorEntityDescription):
    value: Callable[[dict], object]


@dataclass(frozen=True, kw_only=True)
class ChDesc(SensorEntityDescription):
    value: Callable[[dict], object]


def _active_name(s: dict) -> str | None:
    return next((c["name"] for c in s.get("channels", []) if c["id"] == s.get("active")), s.get("active"))


OBJECT_SENSORS: tuple[ObjDesc, ...] = (
    ObjDesc(key="status", device_class=SensorDeviceClass.ENUM, options=STATUSES, value=lambda s: s.get("status")),
    ObjDesc(key="active", value=_active_name),
    ObjDesc(key="rtt", native_unit_of_measurement=UnitOfTime.MILLISECONDS, device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0, value=lambda s: s.get("rtt_ms")),
    ObjDesc(key="rx", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, device_class=SensorDeviceClass.DATA_RATE,
            state_class=SensorStateClass.MEASUREMENT, entity_registry_enabled_default=False, value=lambda s: s.get("rx_mbps")),
    ObjDesc(key="tx", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, device_class=SensorDeviceClass.DATA_RATE,
            state_class=SensorStateClass.MEASUREMENT, entity_registry_enabled_default=False, value=lambda s: s.get("tx_mbps")),
    ObjDesc(key="traffic_today", native_unit_of_measurement=UnitOfInformation.GIGABYTES, device_class=SensorDeviceClass.DATA_SIZE,
            suggested_display_precision=1, value=lambda s: (s.get("traffic_days") or [{}])[-1].get("gb")),
    ObjDesc(key="uptime30", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
            value=lambda s: (s.get("uptime30") or {}).get("total_pct")),
    ObjDesc(key="saves30", state_class=SensorStateClass.TOTAL, value=lambda s: (s.get("uptime30") or {}).get("saves")),
    ObjDesc(key="device_uptime", native_unit_of_measurement=UnitOfTime.SECONDS, device_class=SensorDeviceClass.DURATION,
            entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
            value=lambda s: (s.get("device") or {}).get("uptime_s")),
)

CHANNEL_SENSORS: tuple[ChDesc, ...] = (
    ChDesc(key="state", device_class=SensorDeviceClass.ENUM, options=CH_STATES, value=lambda c: c.get("state")),
    ChDesc(key="rtt", native_unit_of_measurement=UnitOfTime.MILLISECONDS, device_class=SensorDeviceClass.DURATION,
           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0, value=lambda c: c.get("rtt_ms")),
    ChDesc(key="loss", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT,
           entity_registry_enabled_default=False, value=lambda c: c.get("loss_pct")),
    ChDesc(key="month", native_unit_of_measurement=UnitOfInformation.GIGABYTES, device_class=SensorDeviceClass.DATA_SIZE,
           suggested_display_precision=1, entity_registry_enabled_default=False, value=lambda c: c.get("month_gb")),
    ChDesc(key="rsrp", native_unit_of_measurement="dBm", device_class=SensorDeviceClass.SIGNAL_STRENGTH,
           state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC, value=lambda c: c.get("rsrp_dbm")),
)


async def async_setup_entry(hass: HomeAssistant, entry: AdaptisHomeEntry, add: AddEntitiesCallback) -> None:
    co = entry.runtime_data
    ents: list[SensorEntity] = []
    for dev_id, snap in co.data.items():
        ents += [ObjectSensor(co, dev_id, d) for d in OBJECT_SENSORS]
        for c in snap.get("channels", []):
            ents += [ChannelSensor(co, dev_id, c["id"], d) for d in CHANNEL_SENSORS if d.key != "rsrp" or c.get("kind") == "lte"]
    add(ents)


class ObjectSensor(AdaptisHomeEntity, SensorEntity):
    entity_description: ObjDesc

    def __init__(self, co, dev_id, desc: ObjDesc) -> None:
        super().__init__(co, dev_id, desc.key)
        self.entity_description = desc

    @property
    def native_value(self):
        return self.entity_description.value(self.snap)

    @property
    def extra_state_attributes(self):
        if self.entity_description.key != "status": return None
        s, d, u = self.snap, self.snap.get("device") or {}, self.snap.get("uptime30") or {}
        return {"last_seen": s.get("last_seen"), "primary": s.get("primary"), "serial": d.get("serial"), "model": d.get("model"),
                "config_version": d.get("config_version"), "uptime30_total_pct": u.get("total_pct"),
                "uptime30_primary_pct": u.get("primary_pct"), "uptime30_saved_s": u.get("saved_s"), "saves30": u.get("saves")}


class ChannelSensor(AdaptisHomeChannelEntity, SensorEntity):
    entity_description: ChDesc

    def __init__(self, co, dev_id, ch_id, desc: ChDesc) -> None:
        super().__init__(co, dev_id, ch_id, desc.key)
        self.entity_description = desc

    @property
    def native_value(self):
        return self.entity_description.value(self.channel)

    @property
    def extra_state_attributes(self):
        base = super().extra_state_attributes
        if self.entity_description.key != "state": return base
        c = self.channel
        return {**base, "kind": c.get("kind"), "desc": c.get("desc"), "down_since": c.get("down_since"), "avail_24h": c.get("avail")}
