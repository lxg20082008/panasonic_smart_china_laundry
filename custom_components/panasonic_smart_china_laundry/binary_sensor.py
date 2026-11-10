# -*- coding: utf-8 -*-
"""二进制传感器：运行/终了/门/童锁/提醒等，供自动化触发。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeviceData
from .const import CATEGORY_DRYER, CATEGORY_WASHER, DOMAIN


def _as_int(value: Any) -> int | None:
    """协议值转 int。"""
    if value is None or value in (255, 65535):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class BinarySpec:
    """二进制传感器规格。"""

    key: str
    name: str
    icon: str
    categories: tuple[str, ...]
    device_class: BinarySensorDeviceClass | None = None
    check: Callable[[dict], bool | None] | None = None


def _eq(key: str, *values: int) -> Callable[[dict], bool | None]:
    """生成「字段值 ∈ values」的判定函数。"""
    def _check(status: dict) -> bool | None:
        num = _as_int(status.get(key))
        if num is None:
            return None
        return num in values
    return _check


ALL_BINARY_SPECS = (
    # 运行状态（两机共用）
    BinarySpec("running", "运转中", "mdi:washing-machine",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               device_class=BinarySensorDeviceClass.RUNNING,
               check=_eq("runingStage", 2)),
    BinarySpec("finished", "运转终了", "mdi:check-circle-outline",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               check=_eq("runingStage", 5)),
    BinarySpec("error", "异常", "mdi:alert-circle",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               device_class=BinarySensorDeviceClass.PROBLEM,
               check=_eq("runingStage", 6)),
    BinarySpec("delay", "预约中", "mdi:clock-outline",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               check=_eq("runingStage", 3, 4)),
    BinarySpec("door", "机门开", "mdi:door-open",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               device_class=BinarySensorDeviceClass.DOOR,
               check=_eq("gateStatus", 0)),  # 0=门未关闭（官方 JS 实证）
    BinarySpec("child_lock", "童锁", "mdi:lock",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               device_class=BinarySensorDeviceClass.LOCK,
               check=_eq("childLock", 1)),
    BinarySpec("remote", "远程控制", "mdi:remote",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               check=_eq("remoteStatus", 1)),
    BinarySpec("filter_remind", "滤网需清洁", "mdi:air-filter",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               device_class=BinarySensorDeviceClass.PROBLEM,
               check=_eq("filterCleanReminder", 1)),
    # 洗衣机独有
    BinarySpec("detergent_lack", "洗衣液不足", "mdi:bottle-tonic-alert-outline",
               (CATEGORY_WASHER,),
               device_class=BinarySensorDeviceClass.PROBLEM,
               check=_eq("detergentLack", 1)),
    BinarySpec("softener_lack", "柔软剂不足", "mdi:bottle-tonic-alert-outline",
               (CATEGORY_WASHER,),
               device_class=BinarySensorDeviceClass.PROBLEM,
               check=_eq("softenerLack", 1)),
    # 烘护机独有
    BinarySpec("water_full", "水箱已满", "mdi:water-alert",
               (CATEGORY_DRYER,),
               device_class=BinarySensorDeviceClass.PROBLEM,
               check=_eq("waterFullReminder", 1)),
    BinarySpec("care_agent_lack", "护理剂不足", "mdi:bottle-tonic-alert-outline",
               (CATEGORY_DRYER,),
               device_class=BinarySensorDeviceClass.PROBLEM,
               check=_eq("careAgentLack", 1)),
)


class PanasonicLaundryBinary(BinarySensorEntity):
    """通用二进制传感器实体。"""

    _attr_has_entity_name = True

    def __init__(self, device: DeviceData, spec: BinarySpec) -> None:
        self._device = device
        self._spec = spec
        self._attr_unique_id = f"{device.device_id}_{spec.key}"
        self._attr_name = spec.name
        self._attr_icon = spec.icon
        self._attr_device_class = spec.device_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.device_id)},
            "name": device.name,
            "manufacturer": "Panasonic",
            "model": (
                "XQG100-L188" if device.category == CATEGORY_WASHER
                else "FDC-L1026D"
            ),
        }

    @property
    def available(self) -> bool:
        return self._device.coordinator.last_update_success

    @property
    def is_on(self) -> bool | None:
        status = self._device.coordinator.data
        if not status:
            return None
        return self._spec.check(status)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """为每台设备创建二进制传感器。"""
    entities: list[PanasonicLaundryBinary] = []
    for device in hass.data[DOMAIN][entry.entry_id]["devices"]:
        for spec in ALL_BINARY_SPECS:
            if device.category in spec.categories:
                entities.append(PanasonicLaundryBinary(device, spec))
    async_add_entities(entities)
