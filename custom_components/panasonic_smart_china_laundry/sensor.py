# -*- coding: utf-8 -*-
"""传感器实体：运行阶段/程序/参数/提醒等只读监控。

实机验证字段（WDevGetStatusInfoBD158）：
- 洗衣机 XQG100-L188：135 字段
- 烘护机 FDC-L1026D：131 字段
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import DeviceData
from .const import (
    CATEGORY_DRYER,
    CATEGORY_WASHER,
    CHILD_LOCK,
    DOMAIN,
    DRY_TYPE,
    GATE_STATUS,
    LEVEL_TEXT,
    RUNING_STAGE,
    RUNING_STATUS,
    SPIN_SPEED,
    TEMPERATURE,
    WASH_MODEL,
    WASHER_PROGRAMS,
    WATER_LEVEL,
)

_LOGGER = logging.getLogger(__name__)


def _as_int(value: Any) -> int | None:
    """协议值转 int，无效值返回 None。"""
    if value is None or value in (255, 65535):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _program_name(value: Any) -> str | None:
    """程序编号 → 程序名。"""
    num = _as_int(value)
    if num is None:
        return None
    return WASHER_PROGRAMS.get(num, f"程序{num}")


@dataclass(frozen=True)
class SensorSpec:
    """传感器规格。"""

    key: str                      # 协议字段名
    name: str                     # 显示名
    icon: str
    categories: tuple[str, ...]   # 适用品类
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    unit: str | None = None       # 数值传感器单位
    mapper: Callable[[Any], StateType] | None = None
    options: list[str] | None = None  # 枚举选项（enum 传感器）
    state_attr: str | None = None     # 提取实体属性（默认读 state）


# 通用规格（两机共用）
_COMMON = (
    SensorSpec("runingStage", "运行阶段", "mdi:washing-machine",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               mapper=lambda v: RUNING_STAGE.get(_as_int(v), _as_int(v)),
               options=list(RUNING_STAGE.values())),
    SensorSpec("runingStatus", "运行状态", "mdi:play-pause",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               mapper=lambda v: RUNING_STATUS.get(_as_int(v), _as_int(v)),
               options=list(RUNING_STATUS.values())),
    SensorSpec("program", "当前程序", "mdi:format-list-numbered",
               (CATEGORY_WASHER, CATEGORY_DRYER), mapper=_program_name),
    SensorSpec("runingTimeResidual", "剩余时间", "mdi:timer-outline",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               device_class=SensorDeviceClass.DURATION, unit="min"),
    SensorSpec("runingTimeTotal", "总运行时间", "mdi:timer-sand",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               device_class=SensorDeviceClass.DURATION, unit="min"),
    SensorSpec("timeDelayResidual", "预约剩余", "mdi:timer-clock-outline",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               device_class=SensorDeviceClass.DURATION, unit="min"),
    SensorSpec("childLock", "童锁", "mdi:lock",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               mapper=lambda v: CHILD_LOCK.get(_as_int(v), _as_int(v)),
               options=list(CHILD_LOCK.values())),
    SensorSpec("gateStatus", "机门", "mdi:door",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               mapper=lambda v: GATE_STATUS.get(_as_int(v), _as_int(v)),
               options=list(GATE_STATUS.values())),
    SensorSpec("remoteStatus", "远程控制", "mdi:remote",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("filterCleanReminder", "滤网清洁提醒", "mdi:air-filter",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               mapper=lambda v: {0: "无需", 1: "需清洁"}.get(_as_int(v), _as_int(v)),
               options=["无需", "需清洁"]),
    SensorSpec("waterTemp", "水温", "mdi:thermometer",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               device_class=SensorDeviceClass.TEMPERATURE, unit="°C"),
    SensorSpec("washModel", "洗涤模式", "mdi:swap-horizontal",
               (CATEGORY_WASHER, CATEGORY_DRYER),
               mapper=lambda v: WASH_MODEL.get(_as_int(v), _as_int(v)),
               options=list(WASH_MODEL.values())),
)

# 洗衣机规格
_WASHER = (
    SensorSpec("temperature", "温度设置", "mdi:thermometer-lines",
               (CATEGORY_WASHER,),
               mapper=lambda v: TEMPERATURE.get(_as_int(v), _as_int(v)),
               options=list(TEMPERATURE.values())),
    SensorSpec("spinSpeed", "脱水转速", "mdi:speedometer",
               (CATEGORY_WASHER,),
               mapper=lambda v: SPIN_SPEED.get(_as_int(v), _as_int(v)),
               options=list(SPIN_SPEED.values())),
    SensorSpec("waterLevel", "水位", "mdi:waves",
               (CATEGORY_WASHER,),
               mapper=lambda v: WATER_LEVEL.get(_as_int(v), _as_int(v)),
               options=list(WATER_LEVEL.values())),
    SensorSpec("dryType", "烘干类型", "mdi:white-balance-sunny",
               (CATEGORY_WASHER,),
               mapper=lambda v: DRY_TYPE.get(_as_int(v), _as_int(v)),
               options=list(DRY_TYPE.values())),
    SensorSpec("washTime", "洗涤时间", "mdi:clock-start",
               (CATEGORY_WASHER,), unit="min"),
    SensorSpec("rinseTime", "漂洗回数", "mdi:rotate-3d-variant",
               (CATEGORY_WASHER,), unit="回"),
    SensorSpec("spinTime", "脱水时间", "mdi:clock-end",
               (CATEGORY_WASHER,), unit="min"),
    SensorSpec("dryTime", "烘干时间", "mdi:clock-end",
               (CATEGORY_WASHER,), unit="min"),
    SensorSpec("detergent", "智能投放·洗衣液", "mdi:bottle-tonic-outline",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("softener", "智能投放·柔软剂", "mdi:bottle-tonic-plus-outline",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("detergentResidual", "洗衣液余量", "mdi:bottle-tonic-outline",
               (CATEGORY_WASHER,),
               mapper=lambda v: LEVEL_TEXT.get(_as_int(v), _as_int(v)),
               options=list(LEVEL_TEXT.values())),
    SensorSpec("softenerResidual", "柔软剂余量", "mdi:bottle-tonic-plus-outline",
               (CATEGORY_WASHER,),
               mapper=lambda v: LEVEL_TEXT.get(_as_int(v), _as_int(v)),
               options=list(LEVEL_TEXT.values())),
    SensorSpec("detergentLack", "洗衣液不足", "mdi:alert-outline",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "充足", 1: "不足"}.get(_as_int(v), _as_int(v)),
               options=["充足", "不足"]),
    SensorSpec("softenerLack", "柔软剂不足", "mdi:alert-outline",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "充足", 1: "不足"}.get(_as_int(v), _as_int(v)),
               options=["充足", "不足"]),
    SensorSpec("mute", "静音", "mdi:volume-off",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("agPlus", "光动银", "mdi:brightness-7",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("activeFoam", "水氧泡沫净", "mdi:water-opacity",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("cycpump", "离心净水洗", "mdi:autorenew",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("easyIroning", "免熨烫", "mdi:iron",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("extraRinse", "加漂洗", "mdi:waves-arrow-up",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("preWash", "预洗", "mdi:soap",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("nanoe", "nanoeX", "mdi:sparkles",
               (CATEGORY_WASHER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
)

# 烘护机规格
_DRYER = (
    SensorSpec("dryStyle", "烘干风格", "mdi:weather-sunny",
               (CATEGORY_DRYER,), state_class=SensorStateClass.MEASUREMENT),
    SensorSpec("drySpend", "烘干进度", "mdi:progress-clock",
               (CATEGORY_DRYER,), state_class=SensorStateClass.MEASUREMENT),
    SensorSpec("dryMode", "烘干模式", "mdi:white-balance-sunny",
               (CATEGORY_DRYER,)),
    SensorSpec("airVo", "风量", "mdi:fan",
               (CATEGORY_DRYER,)),
    SensorSpec("waterFullReminder", "水箱满提醒", "mdi:water-alert",
               (CATEGORY_DRYER,),
               mapper=lambda v: {0: "正常", 1: "水箱已满"}.get(_as_int(v), _as_int(v)),
               options=["正常", "水箱已满"]),
    SensorSpec("careAgentBuyRemind", "护理剂购买提醒", "mdi:cart-outline",
               (CATEGORY_DRYER,),
               mapper=lambda v: {0: "无需", 1: "需购买"}.get(_as_int(v), _as_int(v)),
               options=["无需", "需购买"]),
    SensorSpec("careAgentLack", "护理剂不足", "mdi:alert-outline",
               (CATEGORY_DRYER,),
               mapper=lambda v: {0: "充足", 1: "不足"}.get(_as_int(v), _as_int(v)),
               options=["充足", "不足"]),
    SensorSpec("delayClothes", "防皱保持", "mdi:tshirt-crew-outline",
               (CATEGORY_DRYER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("washLinkSync", "洗烘联动", "mdi:link",
               (CATEGORY_DRYER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
    SensorSpec("keepFreshen", "清新保持", "mdi:weather-windy",
               (CATEGORY_DRYER,),
               mapper=lambda v: {0: "关", 1: "开"}.get(_as_int(v), _as_int(v)),
               options=["关", "开"]),
)

ALL_SPECS = _COMMON + _WASHER + _DRYER


class PanasonicLaundrySensor(SensorEntity):
    """通用传感器实体（行为由 SensorSpec 驱动）。"""

    _attr_has_entity_name = True

    def __init__(self, device: DeviceData, spec: SensorSpec) -> None:
        self._device = device
        self._spec = spec
        self._attr_unique_id = f"{device.device_id}_{spec.key}"
        self._attr_translation_key = None  # 名称直接用中文
        self._attr_name = spec.name
        self._attr_icon = spec.icon
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class
        if spec.unit:
            self._attr_native_unit_of_measurement = spec.unit
        if spec.options:
            self._attr_options = spec.options
            if spec.device_class is None:
                # HA 2026.x 要求：带 options 的传感器必须是 ENUM 类型
                self._attr_device_class = SensorDeviceClass.ENUM

        # 设备注册信息
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
    def native_value(self) -> StateType:
        """从协议状态中提取值。"""
        status = self._device.coordinator.data
        if not status:
            return None
        if self._spec.key not in status:
            return None
        value = status[self._spec.key]
        if self._spec.mapper:
            return self._spec.mapper(value)
        num = _as_int(value)
        if num is None:
            return None
        if self._spec.device_class == SensorDeviceClass.DURATION:
            # 分钟 → 小时（HA duration 单位）
            return num / 60
        return num


def _specs_for_category(category: str) -> list[SensorSpec]:
    """按品类过滤传感器规格。"""
    return [spec for spec in ALL_SPECS if category in spec.categories]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """为每台设备创建传感器。"""
    entities: list[PanasonicLaundrySensor] = []
    for device in hass.data[DOMAIN][entry.entry_id]["devices"]:
        for spec in _specs_for_category(device.category):
            entities.append(PanasonicLaundrySensor(device, spec))
    async_add_entities(entities)
