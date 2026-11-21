# -*- coding: utf-8 -*-
"""电源与童锁开关（洗衣机 / 烘护机通用）。"""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeviceData
from .const import CATEGORY_WASHER, DOMAIN
from .control import send_control

_LOGGER = logging.getLogger(__name__)

# 开关规格：key / 显示名 / 控制字段 / 设备类
SWITCH_SPECS = (
    ("power", "电源", "powerStatus", SwitchDeviceClass.OUTLET),
    ("childlock", "童锁", "childLock", None),
)


class PanasonicLaundrySwitch(SwitchEntity):
    """通用开关实体（行为由规格驱动）。"""

    _attr_has_entity_name = True

    def __init__(self, device: DeviceData, key: str, name: str,
                 field: str, device_class) -> None:
        self._device = device
        self._key = key
        self._field = field
        self._attr_unique_id = f"{device.device_id}_{key}"
        self._attr_name = name
        self._attr_device_class = device_class
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
        """有状态数据即视为可用。"""
        return self._device.coordinator.last_update_success

    @property
    def is_on(self) -> bool | None:
        """从状态读取；powerStatus 状态里没有时回退到下发缓存。"""
        status = self._device.coordinator.data or {}
        val = status.get(self._field)
        if val is not None:
            return val == 1
        entry_id = self._device.coordinator.config_entry.entry_id
        settings = self.hass.data[DOMAIN][entry_id]["settings"]
        cached = settings.get(self._device.device_id, {}).get(self._field)
        return cached == 1 if cached is not None else None

    async def async_turn_on(self, **kwargs) -> None:
        """下发开启指令。"""
        await self._async_set(1)

    async def async_turn_off(self, **kwargs) -> None:
        """下发关闭指令。"""
        await self._async_set(0)

    async def _async_set(self, value: int) -> None:
        entry_id = self._device.coordinator.config_entry.entry_id
        try:
            result = await send_control(
                self.hass, entry_id, self._device, {self._field: value}
            )
            _LOGGER.info("%s 下发 %s=%s，结果 %s",
                         self._device.name, self._field, value, result)
        except Exception as exc:  # 下发失败如实抛出给 HA 记录
            _LOGGER.error("%s 下发 %s=%s 失败: %s",
                          self._device.name, self._field, value, exc)
            raise


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """为每台设备创建电源与童锁开关。"""
    entities: list[PanasonicLaundrySwitch] = []
    for device in hass.data[DOMAIN][entry.entry_id]["devices"]:
        for key, name, field, device_class in SWITCH_SPECS:
            entities.append(
                PanasonicLaundrySwitch(device, key, name, field, device_class)
            )
    async_add_entities(entities)
