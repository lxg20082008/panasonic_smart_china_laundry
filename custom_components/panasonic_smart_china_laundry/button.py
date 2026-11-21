# -*- coding: utf-8 -*-
"""启动 / 暂停按钮（洗衣机 / 烘护机通用）。

启动指令实机抓包验证（2026-11-21）：在设置快照基础上携带
runingStatus=1 + startType=1 + smartCloudProgram=0。
"""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeviceData
from .const import CATEGORY_WASHER, DOMAIN
from .control import send_control

_LOGGER = logging.getLogger(__name__)

BUTTON_SPECS = (
    ("start", "启动", {"runingStatus": 1, "startType": 1, "smartCloudProgram": 0}),
    ("pause", "暂停", {"runingStatus": 0}),
)


class PanasonicLaundryButton(ButtonEntity):
    """启动 / 暂停按钮。"""

    _attr_has_entity_name = True

    def __init__(self, device: DeviceData, key: str, name: str,
                 overrides: dict) -> None:
        self._device = device
        self._overrides = overrides
        self._attr_unique_id = f"{device.device_id}_{key}"
        self._attr_name = name
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

    async def async_press(self) -> None:
        """下发启动 / 暂停指令。"""
        entry_id = self._device.coordinator.config_entry.entry_id
        try:
            result = await send_control(
                self.hass, entry_id, self._device, dict(self._overrides)
            )
            _LOGGER.info("%s 下发 %s，结果 %s",
                         self._device.name, self._overrides, result)
        except Exception as exc:
            _LOGGER.error("%s 下发 %s 失败: %s",
                          self._device.name, self._overrides, exc)
            raise


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """为每台设备创建启动 / 暂停按钮。"""
    entities: list[PanasonicLaundryButton] = []
    for device in hass.data[DOMAIN][entry.entry_id]["devices"]:
        for key, name, overrides in BUTTON_SPECS:
            entities.append(PanasonicLaundryButton(device, key, name, overrides))
    async_add_entities(entities)
