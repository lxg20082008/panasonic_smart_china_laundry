# -*- coding: utf-8 -*-
"""设备控制 token 计算。

与官方 web 控制台 js/common/common.js setSessionStorage 的算法一致：
  equipType = deviceId.split('_品类_')[1]      （后缀保持原大小写）
  stoken    = MAC后6位 + '_品类_' + MAC前6位   （MAC 大写）
  token     = sha512(sha512(stoken) + '_' + equipType)
"""
from __future__ import annotations

import hashlib


class DeviceTokenError(ValueError):
    """设备 ID 格式无效时抛出。"""


def generate_device_token(device_id: str) -> str:
    """根据 deviceId（格式 MAC_品类_后缀）计算设备控制 token。"""
    parts = device_id.split("_", 2)
    if len(parts) < 3:
        raise DeviceTokenError(
            f"无效的 deviceId 格式: {device_id}（应为 MAC_品类_后缀）"
        )
    mac_part, category, suffix = parts
    mac_part = mac_part.upper()
    category = category.upper()
    # 后缀保持原始大小写（服务器按 deviceId 原样计算，见上游 token.py 注释）

    if len(mac_part) < 6:
        raise DeviceTokenError(f"deviceId 中 MAC 部分过短: {device_id}")

    stoken = f"{mac_part[6:]}_{category}_{mac_part[:6]}"
    inner = hashlib.sha512(stoken.encode()).hexdigest()
    return hashlib.sha512(f"{inner}_{suffix}".encode()).hexdigest()
