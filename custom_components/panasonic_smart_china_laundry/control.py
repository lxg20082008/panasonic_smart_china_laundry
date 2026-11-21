# -*- coding: utf-8 -*-
"""控制快照构造。

协议要点（2026-11-21 实机抓包验证）：
- 控制接口 WDevSetStatusInfoCommon 的 params 是「完整快照」：必须携带
  全部控制字段，只改目标字段，服务器不接受部分字段。
- 构造优先级：模板默认值 < 设备状态(BD158) < 集成缓存(历史下发值) < 本次指令。
- 状态字段与控制字段不完全同名（如 washCycleOrg→washCycle），
  经 STATUS_TO_PARAMS 映射。
"""
from __future__ import annotations

from .const import (
    CATEGORY_WASHER,
    DOMAIN,
    PARAMS_DRYER,
    PARAMS_WASHER,
    STATUS_TO_PARAMS,
)


def build_params(
    category: str,
    status: dict,
    cached: dict | None,
    overrides: dict,
) -> dict:
    """构造完整控制快照。

    参数：
    - category: 品类（0600 洗衣机 / 0610 烘护机）
    - status: 最近一次 BD158 状态（字段值）
    - cached: 集成缓存的上次下发字段（状态里没有的字段靠它保持连贯）
    - overrides: 本次要修改的字段
    """
    template = PARAMS_WASHER if category == CATEGORY_WASHER else PARAMS_DRYER
    params = dict(template)

    # 1) 状态里同名字段覆盖（None 跳过）
    for key in params:
        val = status.get(key)
        if val is not None:
            params[key] = val

    # 2) 状态映射字段
    for src, dst in STATUS_TO_PARAMS.items():
        if dst in params:
            val = status.get(src)
            if val is not None:
                params[dst] = val

    # 3) 缓存值覆盖（历史下发的 powerStatus 等状态里没有的字段）
    if cached:
        for key, val in cached.items():
            if key in params and val is not None:
                params[key] = val

    # 4) 本次指令最高优先级
    params.update(overrides)
    return params


def merge_cache(cached: dict, overrides: dict) -> dict:
    """把本次下发的字段合并进缓存，返回新缓存。"""
    new = dict(cached or {})
    new.update(overrides)
    return new


async def send_control(
    hass,
    entry_id: str,
    device,
    overrides: dict,
) -> dict:
    """下发控制指令：构造快照 → 调 API → 更新缓存 → 触发状态刷新。

    实机验证：服务器返回 {"todoId": N}（按设备递增的执行任务号）。
    """
    data = hass.data[DOMAIN][entry_id]
    api = data["api"]
    settings = data["settings"]
    status = device.coordinator.data or {}
    cached = settings.get(device.device_id)
    params = build_params(device.category, status, cached, overrides)
    result = await api.set_status(device.device_id, params)
    settings[device.device_id] = merge_cache(cached, overrides)
    await device.coordinator.async_request_refresh()
    return result
