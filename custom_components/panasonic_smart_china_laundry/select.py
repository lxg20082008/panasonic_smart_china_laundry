# -*- coding: utf-8 -*-
"""设置类选择器：程序 / 水温 / 转速 / 水位 / 烘干类型 / 烘干风格。

选项显示中文名，下发时反查协议数值 ID。
"""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeviceData
from .const import (
    CATEGORY_DRYER,
    CATEGORY_WASHER,
    DOMAIN,
    DRY_STYLE,
    DRY_TYPE,
    DRYER_L1026D_PROGRAMS,
    SPIN_SPEED,
    TEMPERATURE,
    WATER_LEVEL,
    WASHER_L188_PROGRAMS,
    WASHER_PROGRAMS,
)
from .control import send_control

_LOGGER = logging.getLogger(__name__)

SELECT_SPECS = {
    CATEGORY_WASHER: (
        ("program", "程序", WASHER_L188_PROGRAMS, WASHER_PROGRAMS),
        ("temperature", "水温", [0, 1, 2, 3, 4, 6, 7, 8, 9, 10], TEMPERATURE),
        ("spinSpeed", "脱水转速", [0, 2, 4, 5, 7, 9, 11, 15], SPIN_SPEED),
        ("waterLevel", "水位", [0, 1, 2, 4], WATER_LEVEL),
        ("dryType", "烘干类型", [0, 1, 2, 3, 4, 5, 6, 7], DRY_TYPE),
    ),
    CATEGORY_DRYER: (
        ("program", "程序", DRYER_L1026D_PROGRAMS, WASHER_PROGRAMS),
        ("dryStyle", "烘干风格", [1, 2], DRY_STYLE),
        ("dryType", "烘干类型", [0, 1, 2, 3, 4, 5, 6, 7], DRY_TYPE),
    ),
}


class PanasonicLaundrySelect(SelectEntity):
    """通用选择器实体（行为由规格驱动）。"""

    _attr_has_entity_name = True

    def __init__(self, device: DeviceData, key: str, name: str,
                 values: list, names: dict) -> None:
        self._device = device
        self._key = key
        self._values = values
        self._names = names
        self._name_to_id = {names[v]: v for v in values}
        self._attr_unique_id = f"{device.device_id}_{key}"
        self._attr_name = name
        self._attr_options = [names[v] for v in values]
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
    def current_option(self):
        """从状态读取当前值并转为名称。"""
        status = self._device.coordinator.data or {}
        val = status.get(self._key)
        if val is None:
            return None
        try:
            return self._names[int(val)]
        except (KeyError, TypeError, ValueError):
            return None

    async def async_select_option(self, option: str) -> None:
        """下发选择指令（名称反查协议 ID）。"""
        value = self._name_to_id.get(option)
        if value is None:
            raise ValueError(f"无效选项: {option}")
        entry_id = self._device.coordinator.config_entry.entry_id
        try:
            result = await send_control(
                self.hass, entry_id, self._device, {self._key: value}
            )
            _LOGGER.info("%s 下发 %s=%s(%s)，结果 %s",
                         self._device.name, self._key, option, value, result)
        except Exception as exc:
            _LOGGER.error("%s 下发 %s=%s 失败: %s",
                          self._device.name, self._key, option, exc)
            raise


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """为每台设备创建选择器。"""
    entities = []
    for device in hass.data[DOMAIN][entry.entry_id]["devices"]:
        for key, name, values, names in SELECT_SPECS.get(device.category, ()):
            entities.append(PanasonicLaundrySelect(device, key, name, values, names))
    async_add_entities(entities)
