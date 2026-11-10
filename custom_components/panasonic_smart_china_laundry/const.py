# -*- coding: utf-8 -*-
"""常量定义：接口地址、品类、程序名映射、状态枚举。

协议来源（实机验证 2026-11-09）：
- 松下智能家电 App 中国区云接口 app.psmartcloud.com
- 洗衣机 XQG100-L188（品类 0600、subType 32）
- 烘护机 FDC-L1026D（品类 0610、subType 29）
- 状态接口：WDevGetStatusInfoBD158（洗衣机 135 字段 / 烘护机 131 字段）
- 枚举与程序名：官方 web 控制台 js（collocation.js / constants.js）
"""
from __future__ import annotations

DOMAIN = "panasonic_smart_china_laundry"

# 云接口地址
API_BASE = "https://app.psmartcloud.com/App/"
URL_GET_TOKEN = API_BASE + "UsrGetToken"
URL_LOGIN = API_BASE + "UsrLogin"
URL_GET_DEVICES = API_BASE + "UsrGetBindDevInfo"
URL_GET_STATUS = API_BASE + "WDevGetStatusInfoBD158"

# 轮询间隔（秒）
POLL_INTERVAL = 30

# 本集成支持的品类
SUPPORTED_CATEGORIES = {"0600", "0610"}
CATEGORY_WASHER = "0600"   # 洗衣机
CATEGORY_DRYER = "0610"    # 烘护机

# 运行阶段 runingStage（两机共用）
RUNING_STAGE = {
    0: "待机",
    1: "设定中",
    2: "运转中",
    3: "预约中",
    4: "预约中",
    5: "运转终了",
    6: "异常",
    7: "中途关机",
}

# 运行状态 runingStatus
RUNING_STATUS = {0: "暂停", 1: "运行"}

# 童锁 childLock
CHILD_LOCK = {0: "关", 1: "开"}

# 机门 gateStatus（官方 JS 实证：=== 0 时提示「机门未关闭」并阻止启动）
# 0 = 机门未关闭（开），1 = 机门已关闭
GATE_STATUS = {0: "开", 1: "关"}

# 洗涤模式 washModel
WASH_MODEL = {0: "洗涤", 1: "洗干", 2: "烘干", 3: "护理", 4: "健康"}

# 温度设置 temperature
TEMPERATURE = {
    0: "冷水", 1: "30℃", 2: "40℃", 3: "50℃", 4: "60℃",
    6: "70℃", 7: "80℃", 8: "90℃", 9: "95℃", 10: "100℃",
}

# 脱水转速 spinSpeed（洗衣机）
SPIN_SPEED = {
    0: "500r/min", 2: "700r/min", 4: "900r/min", 5: "1000r/min",
    7: "1200r/min", 9: "1400r/min", 11: "1600r/min", 15: "0",
}

# 水位 waterLevel
WATER_LEVEL = {0: "少量", 1: "低", 2: "中", 4: "高"}

# 烘干类型 dryType
DRY_TYPE = {
    0: "自动", 1: "低温", 2: "定时30分", 3: "定时60分", 4: "定时90分",
    5: "定时120分", 6: "定时180分", 7: "定时210分",
}

# 洗衣机程序名（官方 collocation.js 注释表）
WASHER_PROGRAMS = {
    0: "一键智洗", 1: "棉织物", 2: "化纤", 3: "羊毛", 4: "丝绸内衣",
    5: "运动服", 6: "衬衫", 7: "混合洗", 8: "羽绒服", 9: "筒洗净",
    10: "夜洗", 11: "大物", 12: "顽渍洗", 13: "超快速", 14: "快速洗",
    15: "除菌", 16: "节能洗", 17: "能效", 18: "A+", 19: "单脱水模式",
    20: "棉普通", 21: "随心洗", 22: "超柔", 23: "NANOE除菌", 24: "户外服",
    25: "牛仔", 26: "除螨", 27: "Nanoe除味", 28: "Nanoe防霉", 29: "净漂",
    30: "亮彩", 31: "单洗", 32: "单漂洗", 33: "单脱水", 34: "自动烘干",
    35: "低温烘干", 36: "定时烘干", 37: "单烘干", 38: "active speed",
    39: "衣领袖口", 40: "油渍洗", 41: "泥渍洗", 42: "棉质节能洗",
    43: "ECONAVI", 44: "自投入保养", 45: "清屑洁筒", 46: "Daily",
    47: "COTTON_A", 48: "COTTON_ECO_A", 49: "nanoeX护衣",
    50: "nanoeX防过敏", 51: "nanoeX除皱", 52: "nanoeX蓬松",
    53: "nanoeX毛皮养护", 54: "nanoeX婴童暖衣", 55: "离心净水洗认证",
    56: "烘干GB模式", 57: "暖衣", 58: "空气洗", 59: "漂+脱",
    60: "除菌空气洗", 64: "羊绒", 65: "针织", 66: "高档衬衫",
    67: "雪纺", 68: "内衣", 69: "晶钻蕾丝", 70: "快烘", 71: "毛巾",
    72: "婴童装", 73: "随心烘", 74: "NanoeX一键智护", 75: "定时暖风",
    76: "NanoeX护衣", 77: "冷风清新", 78: "除螨洗", 79: "焕新空气洗",
    80: "工装校服", 81: "夜间烘", 82: "晒被/被子", 83: "热风暖衣",
}

# XQG100-L188 支持的程序（collocation.js DEV_TYPE_LIST paramIdList）
WASHER_L188_PROGRAMS = [
    12, 5, 6, 2, 25, 21, 1, 8, 11, 3, 4, 14, 33, 15, 78, 7, 16,
    9, 22, 29, 30, 24, 59, 32, 17, 18, 19, 44, 45, 55, 56,
]

# FDC-L1026D 支持的程序（collocation.js DEV_TYPE_LIST paramIdList）
DRYER_L1026D_PROGRAMS = [
    1, 3, 24, 8, 70, 11, 72, 82, 73, 2, 4, 6, 71, 25, 80, 15,
    5, 7, 77, 83, 23, 27, 50, 51, 52, 53,
]

# 洗衣液/柔软剂余量等级 detergentResidual / softenerResidual
LEVEL_TEXT = {0: "关", 1: "低", 2: "中", 3: "高"}
