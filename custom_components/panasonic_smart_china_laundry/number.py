# -*- coding: utf-8 -*-
"""数值设置：洗涤 / 漂洗 / 脱水 / 烘干时间等。"""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeviceData
from .const import CATEGORY_DRYER, CATEGORY_WASHER, DOMAIN
from .control import send_control

_LOGGER = logging.getLogger(__name__)

# 数值规格：key / 显示名 / 最小值 / 最大值 / 步进 / 单位 / 状态读取字段
# read_key 缺省同 key；漂洗次数等状态字段与控制字段不同名时单独指定
NUMBER_SPECS = {
    CATEGORY_WASHER: (
        ("washTime", "洗涤时间", 0, 75, 5, "分钟", None),
        ("rinseCycle", "漂洗次数", 1, 3, 1, "次", "rinseCycleOrg"),
        ("spinTime", "脱水时间", 1, 15, 1, "分钟", None),
    ),
    CATEGORY_DRYER: (
        ("dryTime", "烘干时间", 10, 120, 5, "分钟", None),
    ),
}


class PanasonicLaundryNumber(NumberEntity):
    """通用数值设置实体（行为由规格驱动）。"""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER

    def __init__(self, device: DeviceData, key: str, name: str,
                 minimum: int, maximum: int, step: int, unit: str,
                 read_key) -> None:
        self._device = device
        self._key = key
        self._read_key = read_key or key
        self._attr_unique_id = f"{device.device_id}_{key}"
        self._attr_name = name
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
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
    def native_value(self):
        """从状态读取当前数值。"""
        status = self._device.coordinator.data or {}
        val = status.get(self._read_key)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """下发数值设置指令。"""
        entry_id = self._device.coordinator.config_entry.entry_id
        try:
            result = await send_control(
                self.hass, entry_id, self._device, {self._key: int(value)}
            )
            _LOGGER.info("%s 下发 %s=%s，结果 %s",
                         self._device.name, self._key, int(value), result)
        except Exception as exc:
            _LOGGER.error("%s 下发 %s=%s 失败: %s",
                          self._device.name, self._key, int(value), exc)
            raise


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """为每台设备创建数值设置实体。"""
    entities = []
    for device in hass.data[DOMAIN][entry.entry_id]["devices"]:
        specs = NUMBER_SPECS.get(device.category, ())
        for key, name, minimum, maximum, step, unit, read_key in specs:
            entities.append(
                PanasonicLaundryNumber(device, key, name, minimum, maximum,
                                       step, unit, read_key)
            )
    async_add_entities(entities)
